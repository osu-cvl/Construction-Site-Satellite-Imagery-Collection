"""
This module contains a class used to interface with the Planet api.
"""

__author__ = """Nicholas Kashani Motlagh @ Ohio State University\n
                Aswathnarayan Radhakrishnan @ Ohio State University\n
                Jim Davis @ Ohio State University (Point of Contact, see __email__)\n
                Roman Ilin @ AFRL/RYAP, Wright-Patterson AFB"""
__email__ = 'davis.1719@osu.edu'
__date__ = "2020-08-05"

# Built-in/Generic Imports
from datetime import date, timedelta, datetime
import json
import math
import os
from pathlib import Path
import shutil
import sys
from time import sleep

# Libs
import geopandas as gpd
import numpy as np
from planet import api
from shapely import geometry, affinity
from skimage import io
from urllib3 import exceptions as url_exceptions
import zipfile

# Directory containing the output
output_dir = Path("output")


class PlanetHandlerV2:
    """
    A class which can create and download imagery orders for rows in a GeoDataFrame from extract_sites
    """

    def __init__(self, api_key, image_parameters, gdf):
        """
        Creates a PlanetHandler object which can create and download orders of images for sites in the gdf using an
        api key.
        :param api_key: API key used to download images
        :param image_parameters: Map of parameters used in processing
        :param gdf: The GeoDataFrame containing construction sites
        """
        self.gdf = gdf
        self.client = api.ClientV1(api_key=api_key)
        self.params = image_parameters
        self.item_types = ["PSOrthoTile"]
        self.bundle = []
        if self.params["nir"]:
            self.bundle.append("analytic_sr")
        if self.params["rgb"]:
            self.bundle.append("visual")
        self.day_padding = 5

    def get_dates(self, row):
        """
        A function which returns a list of size num-images which contains evenly spaced tuples of date ranges.
        This function automatically includes date ranges which include the start date and the end date.
        :param row: A row in the dataframe for which to gather date ranges
        :return: A list of tuples containing evenly spaced starting and ending dates.
        """
        # get date objects
        start_date = date.fromisoformat(row["start"])
        end_date = date.fromisoformat(row["end"])
        # find number of days under construction inside start-end window (end - start + 1) - 2
        days_in_range = (end_date - start_date).days - 1
        # find number of images needed in the range
        num_img_within_range = self.params["num-images"] - 2
        # if we want all available images or we request more images than in the construction range, return full window
        if self.params["num-images"] == -1 or num_img_within_range >= days_in_range:
            return [[str(start_date), str(end_date + timedelta(days=1 + self.day_padding))]]

        # create a date list whose first element is a range (start_date, start_date + 1 + padding)
        date_list = [[str(start_date), str(start_date + timedelta(days=1 + self.day_padding))]]
        # i is going to be used as a multiplier, start at 1 and end at num_img_within_range
        for i in range(1, num_img_within_range + 1):
            # compute number of days to add to the start date
            days_add = timedelta(days=math.ceil(i * days_in_range / (num_img_within_range + 1)))
            date_list.append([str(start_date + days_add),
                              str(start_date + days_add + timedelta(days=1 + self.day_padding))])
        # add day after construction to the list
        date_list.append([str(end_date), str(end_date + timedelta(days=1 + self.day_padding))])
        return date_list

    def generate_geoson_geometry(self, row):
        """
        Generates a scaled geoson geometry of a bounding box containing row["geometry"]
        :param row: The row whose geometry will be used to create a geoson geometry
        :return: A scaled geoson geometry for row.
        """
        # Scale the bounding box up
        boxes = affinity.scale(row["geometry"], xfact=math.sqrt(self.params["padding"]),
                               yfact=math.sqrt(self.params["padding"]))
        # Get a geoson geometry
        temp_json = gpd.GeoSeries(boxes).to_json()
        geo_json = json.loads(temp_json)
        return geo_json["features"][0]["geometry"]

    def get_filter(self, row, left_date, right_date):
        """
        Creates a filter for an order for row. A geometry filter, date filter, and permission filter are combined into
        an and filter.
        :param row: The row of the dataframe for which to create a filter
        :param left_date: The earliest date to include in the filter
        :param right_date: The latest date to include in the filter
        :return: An and filter containing geometry filter, date filter, and permission filter.
        """
        geo_json_geometry = self.generate_geoson_geometry(row)
        # Create a filter using the geoson geometry
        geo_filter = api.filters.geom_filter(geo_json_geometry)
        # Create a filter using left and right dates
        date_filter = api.filters.date_range("acquired", gte=str(left_date), lte=str(right_date))
        # Create a permission filter
        and_filter = api.filters.and_filter(geo_filter, date_filter)
        if self.params["rgb"]:
            permission_filter = api.filters.permission_filter('assets.visual:download')
            and_filter = api.filters.and_filter(and_filter, permission_filter)
        if self.params["nir"]:
            permission_filter = api.filters.permission_filter('assets.analytic_sr:download')
            and_filter = api.filters.and_filter(and_filter, permission_filter)
        # and_filter = api.filters.and_filter(geo_filter, date_filter, permission_filter)
        permission_filter = api.filters.permission_filter(f'assets:download')
        and_filter = api.filters.and_filter(and_filter, permission_filter)
        # Return an and filter
        return and_filter

    def update_item_ids(self, item_ids, and_filter, row, full_window=False):
        """
        Will update dictionary item_ids with new item ids from request.
        :param item_ids: Map of ids of items to download
        :param and_filter: A filter used to search for new items
        :param row: A row in the dataframe to get new items
        :param full_window: True when all images are requested
        :return: None
        """
        # create a search request
        request = api.filters.build_search_request(and_filter, self.item_types)
        # try to get the request
        retry = 0
        search_result = None
        while retry < 5:
            try:
                search_result = self.client.quick_search(request, sort="acquired asc")
                break
            except api.exceptions.InvalidAPIKey:
                print("Your api key is invalid!")
                sys.exit(2)
            except api.APIException:
                retry += 1
                sleep(1)
        # Server might be down
        if search_result is None:
            return
        for page in search_result.iter():
            for item in page.items_iter(250):
                # Check that the tile contains the full geometry
                acquired_date = item["properties"]["acquired"].split("T")[0]
                item_geo = geometry.shape(item["geometry"])
                if item_geo.contains(row["geometry"]):
                    if acquired_date not in item_ids.keys():
                        item_ids[acquired_date] = item["id"]
                        if not full_window:
                            return

    def create_order(self, row):
        """
        Create an order for a row in self.gdf.
        :param row: A row for which an order will be created.
        :return: If an order was created, a tupe (order, chain_id) otherwise None
        """
        cutoff_date = date(day=19, month=2, year=2017)
        if date.fromisoformat(row["start"]) < cutoff_date:
            if self.params["verbose"]:
                print("\tStart date before 2/19/2017! Skipped!")
            return None
        # get a list of dates for the row
        date_list = self.get_dates(row)
        item_ids = {}
        geo_json_geometry = self.generate_geoson_geometry(row)

        # Update the item_ids map with items from each date range in date_list
        for date_range in date_list:
            and_filter = self.get_filter(row, date_range[0], date_range[1])
            self.update_item_ids(item_ids, and_filter, row, full_window=(len(date_list) == 1))

        # Check that there are items to order
        available_items = [item_ids[k] for k in item_ids.keys()]
        if len(available_items) > 0:
            # list of orders that have been sent
            sent_orders = []
            # n is the max number of items we can submit in an order. We can have at most 500 products per order
            # If RGB and NIR then 250 items per order else, 500 items
            n = 500 // len(self.bundle)
            # split available items into chunks of max number of items
            chunked_items = [available_items[i * n:(i + 1) * n] for i in range((len(available_items) + n - 1) // n)]
            # create an order for each chunk
            for chunk in chunked_items:
                products = []
                for b in self.bundle:
                    product = {
                        "item_type": self.item_types[0],
                        "item_ids": chunk,
                        "product_bundle": b
                    }
                    products.append(product)

                # Create the order
                order_request = {
                    "name": row["chain_id"],
                    "tools": [{
                        "reproject": {
                            "projection": "EPSG:4326",
                            "kernel": "near"
                        }
                    },
                        {
                            "clip": {
                                "aoi": geo_json_geometry
                            }
                        }
                    ],
                    "products": products,
                    "notifications": {
                        "email": self.params["email"]
                    },
                    "delivery": {
                        "archive_type": "zip",
                        "single_archive": True,
                        "archive_filename": "{{name}}_{{order_id}}.zip"
                    }
                }
                # Try to send the order
                try:
                    sent_order = self.client.create_order(order_request)
                    sent_orders.append([sent_order.get(), row["chain_id"], item_ids])
                except api.APIException as e:
                    print(f"\tCould not get order {row['chain_id']}. Exception: {e}")
            if len(sent_orders) > 0:
                return sent_orders
            else:
                return None
        elif self.params["verbose"]:
            print("\tCould not submit order. No available items!")

    def construct_order_list(self):
        """
        Constructs a list of orders from order_log.txt
        :return: The constructed order_list
        """
        order_list = []
        with open("order_log.txt", 'r') as f:
            for line in f:
                line = line.split(",")
                line[-1] = line[-1].strip("\n")
                order = self.client.get_individual_order(line[0]).get()
                chain_id = line[1]
                order_list.append([order, chain_id])
        return order_list

    def download_orders(self):
        """
        Downloads orders from order_list.
        :return: None
        """
        # Recover the order list from order_log.txt
        order_list = self.construct_order_list()
        completed_order_indices = []
        # try to download orders
        try:
            for order_info_index, order_info in enumerate(order_list):
                # get path to planet dir
                planet_path = output_dir / f"{order_info[1]}/images/planet"
                # Get the id of the order
                order_id = order_info[0]["id"]
                # Check that the current order is still running
                if order_info[0]["state"] not in ["success", "failed", "partial"]:
                    if order_info[0]["state"] != "running" and self.params["verbose"]:
                        print(f"\tOrder {order_id} is {order_info[0]['state']}")
                    try:
                        order_info[0] = self.client.get_individual_order(order_id).get()
                    except api.APIException as e:
                        print(f"\tError getting order. Order will remain in order_log. Exception: {e}")
                else:
                    # The order is not running
                    # Check that the order was a success
                    if self.params["verbose"]:
                        if order_info[0]["state"] == "failed":
                            print(f"\tOrder {order_id} failed for {order_info[1]}.")
                        elif order_info[0]["state"] == "partial":
                            print(f"\tOrder {order_id} failed (only partially available) for {order_info[1]}.")
                    if order_info[0]["state"] == "success":
                        correct_link = None
                        # make a temp dir for zip
                        write_path = planet_path / f"temp"
                        if not write_path.is_dir():
                            write_path.mkdir()
                        for item in order_info[0]["_links"]["results"]:
                        # Get link for zip
                            if "zip" in item["name"] :
                                correct_link = item["location"]
                                break
                        # Check that the zip link exists
                        if correct_link is None:
                            continue
                        # try to download zip
                        keep_trying = True
                        sleep_time = .2
                        response = None
                        while keep_trying and sleep_time < 120:
                            try:
                                write_func = api.write_to_file(directory=str(write_path))
                                response = self.client.download_location(correct_link, callback=write_func)
                                response.wait()
                                keep_trying = False
                            except api.exceptions.TooManyRequests:
                                response = None
                                sleep_time *= 2
                                sleep(sleep_time)
                        # Check if server failed to return order
                        if response is None:
                            return
                        # Try to unzip into temp
                        try:
                            zip_path = next(write_path.glob("*.zip"))
                            with zipfile.ZipFile(str(zip_path), 'r') as zip_ref:
                                zip_ref.extractall(str(write_path))
                        except StopIteration:
                            continue
                        # Rewrite files in zip to proper directories
                        for file in (write_path / "files").glob("*.tif"):
                            self.rewrite_tif(file, planet_path)
                        # Delete temp
                        shutil.rmtree(str(write_path))
                        # Send notification
                        if self.params["verbose"]:
                            print(f"\tBundle {order_id} downloaded for {order_info[1]}!")

                    # Write blank images for days where no images were captured
                    # Check that all available imagery was selected and this is the last order in the order list
                    # for the current chain_id
                    if self.params["num-images"] == -1 and not any(order_info[1] == chain_id and
                                                                   o_index > order_info_index
                                                                   for o_index, (o, chain_id) in enumerate(order_list)):
                        # Add bands that need blank images
                        bands = []
                        if self.params["rgb"]:
                            bands.append("rgb")
                        if self.params["nir"]:
                            bands.append("nir")

                        for b in bands:
                            img_dir = planet_path / f"{b}"
                            # Check that an image exists in the folder
                            try:
                                any_img_path = next(iter(img_dir.glob("*.png")))
                            except StopIteration:
                                break
                            # Create a blank image to be saved
                            temp_img = io.imread(str(any_img_path))
                            img_size = np.array(temp_img).shape
                            blank_img = np.zeros(img_size).astype(np.uint8)
                            # Get start and end date
                            row = self.gdf.loc[self.gdf["chain_id"] == order_info[1]].iloc[0]
                            start_date = date.fromisoformat(row["start"])
                            end_date = date.fromisoformat(row["end"])
                            empty_dates = [str(start_date + timedelta(days=i)) for i in
                                           range((end_date - start_date).days + 1)]
                            # save a blank image for each day which is missing an image
                            for empty_date in empty_dates:
                                if not (img_dir / f"{empty_date}.png").is_file():
                                    blank_path = img_dir / f"{empty_date}_empty.png"
                                    io.imsave(str(blank_path), blank_img, check_contrast=False)

                    # Add the current order to the completed order indices
                    completed_order_indices.append(order_info_index)

        except api.exceptions.MissingResource:
            print("Download link expired... Please retry.")
        except url_exceptions.ProtocolError:
            print("Connection to host lost... Please retry.")
        except BaseException as e:
            print(f"Something went wrong... {e}. Please retry.")
        finally:
            # Remove orders from the list
            new_order_list, completed_orders = [], []
            for i, order in enumerate(order_list):
                if i in completed_order_indices:
                    completed_orders.append(order)
                else:
                    new_order_list.append(order)
            # Save remaining orders
            if len(new_order_list) > 0:
                self.save_order_list(new_order_list)
                print(f"There are still {len(new_order_list)} orders!")
            else:
                print("No remaining orders!")
                os.remove("order_log.txt")
            # Update the log with completed orders
            if len(completed_orders) > 0:
                self.update_complete_log(completed_orders)

    @staticmethod
    def rewrite_tif(current_file, new_dir):
        """
        Rewrites the tif file downloaded from planet to a png file. In the RGB case, a mask of bad pixels will be saved
        as well as the RGB image. In the NIR case, a png file of scaled surface reflectance values will be saved.
        :param current_file: The path to the tif file.
        :param new_dir: The new directory that contains bands where the png file should be saved to.
        :return: None
        """
        date_name = current_file.parts[-1].split("_")[2]
        if "Visual" in str(current_file):
            bundle_path = "rgb"
        else:
            bundle_path = "nir"
        new_dir = new_dir / f"{bundle_path}"
        # Check if a udm file
        if "udm" in str(current_file):
            date_name = f"{date_name}_udm"
            shutil.copy(str(current_file), str(new_dir / f"{date_name}.tif"))
            os.remove(str(current_file))
            return
        try:
            img = io.imread(str(current_file))
        except BaseException:
            print(f"{str(current_file)} failed to write to PNG. Probably not a TIFF file")
            return
        new_path = new_dir / f"{date_name}.png"
        if bundle_path == "rgb":
            img_arr = np.array(img[:, :, 0:3], dtype=np.uint16)
            io.imsave(str(new_path), img_arr.astype(np.uint8), check_contrast=False)
            img_arr = np.array(img[:, :, 3], dtype=np.uint8)
            new_path = new_dir / f"{date_name}_mask.png"
            io.imsave(str(new_path), img_arr, check_contrast=False)
        else:
            img_arr = np.array(img[:, :, 3])
            img_scaled = img_arr / 10000 * 255
            io.imsave(str(new_path), img_scaled.astype(np.uint8), check_contrast=False)
        os.remove(str(current_file))

    @staticmethod
    def write_to_log(message):
        """
        Writes a message to order_log.txt.
        :param message: A message to be written.
        :return: None
        """
        o = Path("order_log.txt")
        if not o.is_file():
            o.touch()
        with o.open("a") as f:
            f.write(message)

    def bulk_order(self):
        """
        Create orders for all applicable rows in self.gdf, and download them.
        :return: None
        """
        # List of orders to download
        orders_list = []
        for i, r in self.gdf.iterrows():
            # Get order for each desired bundle
            print(f"Orders processing for {r['chain_id']}")
            # Create an order for the row
            created_orders = self.create_order(r)
            if created_orders:
                # Add it to the order list
                orders_list += created_orders
                for o in created_orders:
                    self.write_to_log(f"{o[0]['id']},{o[1]}\n")
                if self.params["verbose"]:
                    print(f"\tOrders created for {r['chain_id']}")

        # Download all the orders that were added
        if len(orders_list) > 0:
            print(f"Last order in list will be {orders_list[-1][0]['id']}")

    @staticmethod
    def save_order_list(order_list):
        """
        Saves a list of orders to order_log.txt.
        :param order_list: A list of orders to be saved.
        :return: None
        """
        order_log = Path("order_log.txt")
        with order_log.open("w") as f:
            for order_info in order_list:
                f.write(f"{order_info[0]['id']},{order_info[1]}\n")

    @staticmethod
    def update_complete_log(order_list):
        """
        Appends the completed orders to order_log_complete.txt.
        :param order_list: A list of complete orders.
        :return: None
        """
        complete_order_log = Path("order_log_complete.txt")
        with complete_order_log.open("a") as f:
            f.write(f"{str(datetime.now())}\n")
            for order_info in order_list:
                f.write(f"{order_info[0]['id']},{order_info[0]['state']},{order_info[1]}\n")
            f.write(f"{'*' * 15}\n")
