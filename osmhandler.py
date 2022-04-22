"""
This module contains a class which can interact with osm files. The module is primarily used to extract ways from osm
files using the OSMHandler class. Often times the class is used to generate shape files of ways under construction.
This class can also be used to identify a boundary tag by applying the entire daily snapshot and extracting relations as
well as ways.
"""

__author__ = """Nicholas Kashani Motlagh @ Ohio State University\n
                Aswathnarayan Radhakrishnan @ Ohio State University\n
                Jim Davis @ Ohio State University (Point of Contact, see __email__)\n
                Roman Ilin @ AFRL/RYAP, Wright-Patterson AFB"""
__email__ = 'davis.1719@osu.edu'
__date__ = "2020-08-05"

# Built-in/Generic Imports
from pathlib import Path

# Lib
import geopandas as gpd
import osmium
from osmium._osmium import InvalidLocationError
import shapely.wkb as wkblib
from shapely.geometry import Polygon

# Directory containing the output
output_dir = Path("output/")


class OSMHandler(osmium.SimpleHandler):
    """
    A class that can generate geo data frames and shape files from osm files.
    """
    def __init__(self, uc=None):
        """
        Constructor that takes in a WayChainMap
        :param uc: A WayChainMap of WayChains
        """
        osmium.SimpleHandler.__init__(self)
        # a list of ways from the osm file
        self.osm_data = []
        self.geometry = {}
        self.uc = uc
        self.wkbfab = osmium.geom.WKBFactory()
        self.tags = {}
        self.helpful_descriptors = {}
        self.ways_list = []

    def _way_inventory(self, elem):
        """
        Update the self.osm_data to include the current way.
        :param elem: way that is to be added
        :return: None
        """
        self.osm_data.append(elem.orig_id())
        # find the type of construction of the way
        found = False
        for tag in elem.tags:
            if not found:
                if tag.k == "building":
                    self.tags[elem.orig_id()] = "building"
                    found = True
                elif tag.k == "landuse":
                    self.tags[elem.orig_id()] = "landuse"
                    found = True
        # if no construction tag was found
        # should never happen
        if not found:
            self.tags[elem.orig_id()] = "ERROR"

    def area(self, a):
        """
        A callback function that adds a way to the inventory and adds the geometry of the way to the list.
        :param a: The way to be added
        :return: None
        """
        if a.from_way():
            # check that if there is a uc then the way id is in a waychain in a map before adding way polygon
            if self.uc is None or a.orig_id() in self.uc.get_map_ways():
                multipolygon_geo = self._create_multipolygon(a)
                if multipolygon_geo is not None:
                    # save the id
                    self._way_inventory(a)
                    # save a tag that defines the area
                    self._update_descriptors(a)
                    # create polygon and add to list
                    self.geometry[a.orig_id()] = multipolygon_geo
                    self.ways_list.append(a.orig_id())
        else:
            # create a new multipolygon from the relation
            multipolygon_geo = self._create_multipolygon(a)
            if multipolygon_geo is not None:
                # save the id
                self._update_descriptors(a)
                # create polygon and add to list
                self.geometry[a.id] = multipolygon_geo

    def _create_multipolygon(self, area):
        """
        Creates a multipolygon from the area
        :param area: The area that a multipolygon should be created from
        :return: A wkb formatted multipolygon or None if there was an error
        """
        try:
            # build the polygon
            building_wkb = self.wkbfab.create_multipolygon(area)
            return wkblib.loads(building_wkb, hex=True)
        except InvalidLocationError:
            return None
        except RuntimeError:
            return None

    def _update_descriptors(self, elem):
        """
        This function will find a correct descriptive tag for an element. It prioritizes more descriptive tags over
        building=yes and landuse=residential.
        :param elem: The element that needs a tag
        :return: None
        """
        less_helpful_tags = ["building=yes", "landuse=residential"]
        key_tags = ["landuse", "leisure", "amenity", "aeroway", "barrier", "boundary", "building", "craft", "emergency",
                    "geological", "historic", "man_made", "military", "natural", "office", "power", "public_transport",
                    "shop", "telecom", "tourism"]
        # get the id of the element
        if elem.from_way():
            orig_id = elem.orig_id()
        else:
            orig_id = int(elem.id)

        found = False
        # look for most descriptive tag (tags that are not in less_helpful_tags)
        for tag in elem.tags:
            if tag.k in key_tags and not found and f"{tag.k}={tag.v}" not in less_helpful_tags:
                self.helpful_descriptors[orig_id] = f"{tag.k}={tag.v}"
                found = True
        # look for any key tag if one has not been found
        if not found:
            for tag in elem.tags:
                if tag.k in key_tags and not found:
                    self.helpful_descriptors[orig_id] = f"{tag.k}={tag.v}"
                    found = True
        # there was no tag found for the location
        if not found:
            self.helpful_descriptors[orig_id] = "NO TAG FOUND"

    def _get_geo_dataframe(self, current_date):
        """
        Returns a geo data frame of ways in the inventory as of the current date
        :param current_date: The date for which the final dataframe should be made
        :return: A new dataframe containing ways under construction
        """
        # A list of column names for a dataframe
        data_col_names = ['chain_id', 'geometry', 'start', 'end', 'constr_tag', 'prev_tag', "final_tag"]

        def generate_row(way_id):
            """
            Generates a row containing chain_id, geometry, start, end, construction_tag, previous_tag, final_tag for a
            given way_id.
            :param way_id: The way_id of a way which needs to be added to the dataframe
            :return: A row for a dataframe containing id, geometry
            """
            # find the correct key in the map
            key = self.uc.find_key(way_id)
            geometry = self.uc.map[key].geometry.bounds
            return [key, geometry, str(self.uc.map[key].start), str(current_date),
                    str(self.uc.map[key].construction_type), str(self.uc.map[key].boundary_previous),
                    str(self.uc.map[key].boundary_post)]

        rows = []
        # create a list of rows for the data frame.
        # fill start of fill end comes here
        for way in self.osm_data:
            rows.append(generate_row(way))

        # Create the dataframe
        # make a list of geometries to create the geo dataframe
        restrict_geometry = []
        for r in rows:
            # make a polygon from bounding box coordinates
            bbox = self.uc.map[r[0]].geometry.bounds
            restrict_geometry.append(
                Polygon([(bbox[0], bbox[1]), (bbox[0], bbox[3]), (bbox[2], bbox[3]), (bbox[2], bbox[1]), ]))
        # create the dataframe
        self.df_osm = gpd.GeoDataFrame(rows, columns=data_col_names, geometry=restrict_geometry)
        self.df_osm.crs = 'epsg:4326'
        # sort by start and end date and reset the index
        self.df_osm = self.df_osm.sort_values(by=['start', 'end'])
        self.df_osm = self.df_osm.reset_index(drop=True)
        return self.df_osm

    def generate_single_shape_file(self, current_date, directory):
        """Will generate a single shape file on a given start date and save in directory

        :param current_date: Date of the shape file
        :param directory: Directory for the file to be passed
        :return: None
        """
        # Get a gdf on the current date
        df = self._get_geo_dataframe(current_date)
        # create or locate the directory
        if not directory.is_dir():
            directory.mkdir()
        # extract to shapefile
        df.to_file(driver='ESRI Shapefile', filename=str(directory / f"{str(current_date)}.shp"))

    def update_prev_post_tag(self, sites, way_id, boundary_f_handler, prev=True):
        """
        This will update sites with either new post or prev tags as well as updated chains. It will return a new way id
        if the site is still incomplete.
        :param sites: The WayChainMap containing way_id
        :param way_id: The way whose way chain needs a boundary tag
        :param boundary_f_handler: An osmhandler to the file on the boundary date
        :param prev: A boolean when true means that previous tag is requested. False means a post tag is requested.
        :return: A new way id added to the way chain containing way_id or None if complete
        """
        # confidence thresholds for determining chaining and end tag
        construction_chain_confidence = .5
        tag_confidence = .5
        # get construction polygon on day
        construction_multipolygon = self.geometry[way_id]
        # get polygons and tags of boundary day
        boundary_tags = boundary_f_handler.helpful_descriptors
        boundary_multipolygons = boundary_f_handler.geometry

        # best case we know what the area was before it went under construction
        if way_id in boundary_tags.keys():
            if prev:
                sites.map[sites.find_key(way_id)].boundary_previous = boundary_tags[way_id]
            else:
                sites.map[sites.find_key(way_id)].boundary_post = boundary_tags[way_id]
            return None

        # a list of locations that occupy the construction polygon
        locations_of_interest = []
        # get a list of intersecting polygons
        for boundary_multipoly_key in boundary_multipolygons.keys():
            # check that the new tag isn't in the under construction map and intersects the construction polygon
            if boundary_multipoly_key not in sites.get_map_ways() and \
                    construction_multipolygon.intersects(boundary_multipolygons[boundary_multipoly_key]):
                # Add the key, IOU, and inverse area of the polygon of interest (makes sorting easier)
                locations_of_interest.append([boundary_multipoly_key,
                                              construction_multipolygon.intersection(
                                                  boundary_multipolygons[boundary_multipoly_key]).area /
                                              (construction_multipolygon.union(
                                                  boundary_multipolygons[boundary_multipoly_key]).area),
                                              1/boundary_multipolygons[boundary_multipoly_key].area])
        # sort largest to smallest, first check IOU, then check inverse area of boundary multipolygon
        locations_of_interest.sort(key=lambda x: (x[1], x[2]))
        locations_of_interest.reverse()

        # list of locations which are under construction but do not meet the threshold
        del_locations = []
        if len(locations_of_interest) > 0:
            for boundary_multipoly_key, iou, inv_area_boundary in locations_of_interest:
                if boundary_tags[boundary_multipoly_key] == "landuse=construction" \
                        or boundary_tags[boundary_multipoly_key] == "building=construction":
                    # Make sure we are adding a way to the chain
                    if iou > construction_chain_confidence and boundary_multipoly_key in boundary_f_handler.ways_list:
                        sites.increment_chain(way_id, boundary_multipoly_key, is_prev=prev)
                        sites.update_map(way_id, geo=boundary_multipolygons[boundary_multipoly_key])
                        return boundary_multipoly_key
                    else:
                        del_locations.append([boundary_multipoly_key, iou, inv_area_boundary])

        # remove locations under construction that did not meet the threshold
        for k in del_locations:
            locations_of_interest.remove(k)

        # check there are still possible locations
        if len(locations_of_interest) > 0:
            # go through locations of interest
            for boundary_multipoly_key, iou, __ in locations_of_interest:
                # check that a location of interest is not in error and meets confidence threshold
                if "NO TAG FOUND" not in boundary_tags[boundary_multipoly_key] and iou > tag_confidence:
                    if prev:
                        sites.map[sites.find_key(way_id)].boundary_previous = boundary_tags[boundary_multipoly_key]
                    else:
                        sites.map[sites.find_key(way_id)].boundary_post = boundary_tags[boundary_multipoly_key]
                    sites.update_map(way_id, geo=boundary_multipolygons[boundary_multipoly_key])
                    return None
        # no locations were found so no tag found
        if prev:
            sites.map[sites.find_key(way_id)].boundary_previous = "NO TAG FOUND"
        else:
            sites.map[sites.find_key(way_id)].boundary_post = "NO TAG FOUND"
        return None
