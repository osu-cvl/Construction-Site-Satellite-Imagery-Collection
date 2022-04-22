"""
The purpose of this module is to gather images of construction sites from extract_sites. This module is able to gather
images from Sentinel-2 and Planet Scopes RGB bands and NIR band. When using Sentinel, if a construction site's
start date is prior to  2015-06-23, no image will be gathered. When using Planet, if a construction site's start date is
prior to 2017-02-19, no image will be gathered.
"""

__author__ = """Nicholas Kashani Motlagh @ Ohio State University\n
                Aswathnarayan Radhakrishnan @ Ohio State University\n
                Jim Davis @ Ohio State University (Point of Contact, see __email__)\n
                Roman Ilin @ AFRL/RYAP, Wright-Patterson AFB"""
__email__ = 'davis.1719@osu.edu'
__date__ = "2020-08-05"

# Built-in/Generic Imports
from datetime import date, timedelta
import getopt
import math
import os
from pathlib import Path
import sys

# Libs
import geopandas as gpd
import numpy as np
from PIL import Image
from shapely import affinity
from sentinelhub import SHConfig, WcsRequest, CRS, BBox, MimeType

# Own modules
from planet_helper import PlanetHandlerV2

# Parameters used throughout the module
parameters = {"rgb": False, "nir": False, "source": None, "num-images": -1, "padding": 1, "verbose": False,
              "email": False, "api": None}

# directory where output exists
output_dir = Path("output")


def check_num_images(num_images):
    """
    Checks that num_images is an int >=3 or -1
    :param num_images: The parameter for num-images.
    :return: An int equal to num_images, or None is there is an error.
    """
    try:
        n = int(num_images)
        if n != -1 and n < 3:
            print(f"ERROR: num-images must be >=3 or -1. Got {num_images}")
            return None
        return n
    except ValueError:
        print(f"ERROR: num-images must be an int! Got {num_images}")
        return None


def check_source(s):
    """
    Checks that s is a valid source (either "p" or "s").
    :param s: The parameter to be assigned to source.
    :return: s if s is a valid source, None otherwise.
    """
    if s not in ["s", "p"]:
        print(f"ERROR: {s} is not a valid source. Choose \'s\' or \'p\'.")
        return None
    return s


def check_padding(p):
    """
    Checks that p is a valid value for padding parameter >= 0.
    :param p: The parameter to be assigned to padding.
    :return: An int equal to p or None if invalid p.
    """
    try:
        n = int(p)
        if n <= 0:
            print(f"ERROR: padding must be >0. Got {n}")
            return None
        return n
    except ValueError:
        print(f"ERROR: padding must be an int! Got {p}")
        return None


def check_boolean(name, arg):
    """
    Check that the argument named name is a boolean.
    :param name: Name of the argument passed
    :param arg: Value of the argument
    :return: arg or None if arg is not a boolean
    """
    if not type(arg) == bool:
        print(f"ERROR: {name} is not a boolean!")
        return None
    return arg


def set_params(params):
    """
    Sets a dictionary of parameters to the module parameters.
    :param params: The dictionary containing the possible parameters.
    :return: None
    """
    global parameters
    parameters = {"rgb": False, "nir": False, "source": None, "num-images": 3, "padding": 1, "verbose": False,
                  "email": False, "download-planet": False, "api": None}
    # Check if user providing num-images
    if "num-images" in params.keys():
        parameters["num-images"] = check_num_images(params["num-images"])
    # Check if used providing padding
    if "padding" in params.keys():
        parameters["padding"] = check_padding(params["padding"])
    if "source" in params.keys():
        parameters["source"] = check_source(params["source"])
    if "api" in params.keys():
        parameters["api"] = params["api"]
    if "verbose" in params.keys():
        parameters["verbose"] = check_boolean("verbose", params["verbose"])
    if "email" in params.keys():
        parameters["email"] = check_boolean("email", params["email"])
    if "download-planet" in params.keys():
        parameters["download-planet"] = check_boolean("download-planet", params["download-planet"])
    if "nir" in params.keys():
        parameters["nir"] = check_boolean("nir", params["nir"])
    if "rgb" in params.keys():
        parameters["rgb"] = check_boolean("rgb", params["rgb"])
    for k in parameters.keys():
        if parameters[k] is None:
            print(f"ERROR: Provide a correct value for {k}!")
            sys.exit(2)

def get_input():
    """Get input parameters from user

    :return: a dictionary of input parameters
    """
    global parameters
    # read commandline arguments, first
    fullCmdArguments = sys.argv
    # - further arguments
    argumentList = fullCmdArguments[1:]
    unixOptions = 's:n:p:C:N:v:e'
    gnuOptions = ["source=", "num-images=", "padding=", "rgb", "nir", "verbose", "email", "api", "download"]

    try:
        arguments, remaining = getopt.getopt(argumentList, unixOptions, gnuOptions)
    except getopt.error as err:
        # output error, and return with an error code
        print(str(err))
        sys.exit(2)
    params = {"rgb": False, "nir": False, "source": None, "num-images": 3, "padding": 1, "verbose": False,
              "email": False, "download-planet": False, "api": None}
    # valuate given options
    for currentArgument, currentValue in arguments:
        if currentArgument in ('-C', "--rgb"):
            params["rgb"] = True
        if currentArgument in ('-N', "--nir"):
            params["nir"] = True
        if currentArgument in ('-s', "--source"):
            params["source"] = check_source(currentValue)
        if currentArgument in ('-n', "--num-images"):
            params["num-images"] = check_num_images(currentValue)
        if currentArgument in ('-p', "--padding"):
            params["padding"] = check_padding(currentValue)
        if currentArgument in ('-v', "--verbose"):
            params["verbose"] = True
        if currentArgument in ('-e', "--email"):
            params["email"] = True
        if currentArgument == "--download-planet":
            params["download-planet"] = True
        if currentArgument == "--api":
            params["api"] = currentValue
    for k in params.keys():
        if params[k] is None:
            print(f"ERROR: Provide a correct value for {k}!")
            sys.exit(2)
    return params


class SentinelHandler:
    """
    A class which can download imagery for rows in a GeoDataFrame from extract_sites
    """
    def __init__(self, instance_id, params, gdf):
        """
        Creates a SentinelHandler object which can download imagery for sites in the gdf using an instance id.
        :param instance_id: An instance_id of a Sentinel configuration
        :param params: Map of parameters used in processing
        :param gdf: The GeoDataFrame containing construction sites
        """
        if instance_id is not None:
            config = SHConfig()
            config.instance_id = instance_id
        else:
            config = None
        self.config = config
        self.params = params
        self.gdf = gdf

    def get_dates_sentinel(self, start, end):
        """
        A function which returns a list of size num-images which contains evenly spaced tuples of date ranges.
        This function automatically includes date ranges which include the start date and the day after the end date.
        :param start: Starting date of window to split
        :param end: Ending date of window to split
        :return: A list of tuples containing evenly spaced starting and ending dates.
        """
        # get start and end date objects
        start = date.fromisoformat(start)
        end = date.fromisoformat(end)
        # choose the padding for the date window
        day_padding = 6
        # find number of days under construction
        days_in_range = (end - start).days - 1
        # find number of images needed in the range
        num_img_within_range = self.params["num-images"]-2
        # if we want all images, return the full range
        if self.params["num-images"] == -1 or num_img_within_range >= days_in_range:
            return [[str(start), str(end + timedelta(days=1 + day_padding))]]
        # create a date list whose first element is the image of the start date
        date_list = [[str(start), str(start+timedelta(days=1+day_padding))]]
        # for each img needed in the range
        for i in range(1, self.params["num-images"]-1):
            # compute number of days to add to the start date
            days_add = timedelta(days=math.ceil(i * days_in_range/(num_img_within_range + 1)))
            date_list.append([str(start + days_add), str(start + days_add + timedelta(days=1 + day_padding))])
        # add last date to list
        date_list.append([str(end), str(end+timedelta(days=1 + day_padding))])
        return date_list

    def get_bands_sentinel(self, row):
        """
        A function which saves num-images images of a construction site which are evenly spaced. Images may be RGB or
        NIR.
        :param row: The construction site in a dataframe for which images need to be obtained.
        :return: None
        """

        def get_good_index(imgs_request, dates_request, date_window):
            """
            A function that returns a list of indices from which images should be selected
            :param imgs_request: Full list of images requested
            :param dates_request: Full list of dates requested
            :param date_window: window of dates containing the images
            :return:
            """
            if len(imgs_request) == 0:
                print(f"FAILED TO GET IMAGE {date_window[0]}-{date_window[1]}")
                return None
            else:
                if self.params["num-images"] == -1:
                    # save all indicies
                    good_index = [index for index, _ in enumerate(dates_request)]
                else:
                    # save the first index
                    good_index = [0]
                return good_index
        # Scaled bounding box
        boxes = affinity.scale(row["geometry"], xfact=self.params["padding"], yfact=self.params["padding"]).bounds
        # minx miny maxx maxy
        construction_bbox = BBox(bbox=boxes, crs=CRS.WGS84)
        # Get a list of requested dates
        date_list = self.get_dates_sentinel(row["start"], row["end"])
        # Retrieve imagery
        for d in date_list:
            if self.params["nir"]:
                # Create NIR request
                wms_nir_request = WcsRequest(
                    layer='NIR',
                    bbox=construction_bbox,
                    time=tuple(d),
                    resx='10m',
                    resy='10m',
                    image_format=MimeType.TIFF_d32f,
                    maxcc=100,
                    config=self.config
                )
                # Get imagery
                nir_img = wms_nir_request.get_data()
                # Get dates
                nir_dates = wms_nir_request.get_dates()
                # Get index/indices of best image
                closest_index = get_good_index(nir_img, nir_dates, d)
                if closest_index is not None:
                    chain_id = row['chain_id']
                    for g in closest_index:
                        # Save imagery at each index
                        img_path = output_dir / f"{chain_id}/images/sentinel/nir/{str(nir_dates[g])[:10]}.png"
                        Image.fromarray(nir_img[g].astype(np.uint8)).save(str(img_path))
            if self.params["rgb"]:
                # Create RGB request
                wms_rgb_request = WcsRequest(
                    layer='TRUE-COLOR-S2-L1C',
                    bbox=construction_bbox,
                    time=tuple(d),
                    resx='10m',
                    resy='10m',
                    maxcc=100,
                    config=self.config
                )
                # Get imagery
                rgb_img = wms_rgb_request.get_data()
                # Get dates
                rgb_dates = wms_rgb_request.get_dates()
                # Get index/indices of best image
                closest_index = get_good_index(rgb_img, rgb_dates, d)
                if closest_index is not None:
                    chain_id = row['chain_id']
                    for g in closest_index:
                        # Save imagery at each index
                        img_path = output_dir / f"{chain_id}/images/sentinel/rgb/{str(rgb_dates[g])[:10]}.png"
                        Image.fromarray(rgb_img[g]).save(str(img_path))

    def get_all_imagery(self):
        """
        Get all imagery in self.gdf.
        :return: None
        """
        # start cutoff date
        start_cutoff = date(year=2015, month=6, day=23)
        for _, row in self.gdf.iterrows():
            # Check that the start date is after cutoff
            if date.fromisoformat(row["start"]) < start_cutoff:
                if self.params["verbose"]:
                    print(f"Start date for {row['chain_id']} is before 2015-06-23. Skipped!")
                continue
            if self.params["verbose"]:
                print(f"Getting imagery for {row['chain_id']}")
            # Get sentinel imagery
            self.get_bands_sentinel(row)


def setup(other_gdf=None):
    """
    A function which creates necessary directories for get_bands_sentinel.
    :param other_gdf: A GeoDataFrame containing construction sites for which images should be gathered.
    :return: None
    """
    # Set gdf to none
    gdf = None
    # Get gdf
    collection_filepath = str(output_dir / "collection/collection.shp")
    if other_gdf is not None:
        gdf = other_gdf
    else:
        # Check that the file exists
        if not os.path.isfile(collection_filepath):
            print("No construction sites found!")
            return
        gdf = gpd.read_file(str(collection_filepath))
    # Create directories for gdf
    for i, row in gdf.iterrows():
        # create paths for images
        chain_id = row['chain_id']
        chain_path = Path(f"output/{chain_id}")
        if not chain_path.is_dir():
            chain_path.mkdir()
        images_path = chain_path / "images"
        if not images_path.is_dir():
            images_path.mkdir()
        if parameters["source"] == "p":
            source_path = images_path / "planet"
            if not source_path.is_dir():
                source_path.mkdir()
        else:
            source_path = images_path / "sentinel"
            if not source_path.is_dir():
                source_path.mkdir()
        if parameters["rgb"]:
            rgb_path = source_path / "rgb"
            if not rgb_path.is_dir():
                rgb_path.mkdir()
        if parameters["nir"]:
            nir_path = source_path / "nir"
            if not nir_path.is_dir():
                nir_path.mkdir()


def gather_from_source(gdf):
    """
    Get imagery from source in parameters
    :param gdf: GeoDataFrame of construction sites from extract_sites
    :return: None
    """
    global parameters
    if parameters["source"] == "p":
        # Get images from planet
        planethandler = PlanetHandlerV2(parameters["api"], parameters, gdf)
        if parameters["download-planet"]:
            # Download orders
            planethandler.download_orders()
        else:
            # Create orders
            planethandler.bulk_order()
    else:
        # Get images from sentinel
        sentinelhandler = SentinelHandler(parameters["api"], parameters, gdf)
        sentinelhandler.get_all_imagery()


if __name__ == "__main__":
    # Get input parameters
    parameters = get_input()
    # setup directories needed
    setup()
    # get geodataframe
    collection_file = output_dir / "collection/collection.shp"
    geodf = gpd.read_file(str(collection_file))
    # get image bands for rows
    gather_from_source(geodf)

