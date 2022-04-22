"""
This module contains classes that model a construction chain and a map data structure to hold the chains.
"""

__author__ = """Nicholas Kashani Motlagh @ Ohio State University\n
                Aswathnarayan Radhakrishnan @ Ohio State University\n
                Jim Davis @ Ohio State University (Point of Contact, see __email__)\n
                Roman Ilin @ AFRL/RYAP, Wright-Patterson AFB"""
__email__ = 'davis.1719@osu.edu'
__date__ = "2020-08-05"

# Libs
import geopandas as gpd
from shapely.geometry import box


class WayChain:
    """
    A class used to represent a construction chain in OSM files.
    """
    serial_no = 0

    def __init__(self, way_id, start, end, constr_type, prev, post, geo):
        """
        A constructor for a WayChain object
        :param way_id: The id of the way for which a chain is being made
        :param start: The start date of construction
        :param end: The end date of construction
        :param constr_type: The type of construction
        :param prev: The previous tag
        :param post: The final tag
        :param geo: The geometry of the way
        """
        self.ids = [way_id]
        self.start = start
        self.end = end
        self.construction_type = constr_type
        self.boundary_previous = prev
        self.boundary_post = post
        self.geometry = geo
        self.serial_no = WayChain.serial_no
        WayChain.serial_no += 1

    def __str__(self):
        if self.construction_type == "landuse":
            return f"{self.start}\t{self.end}\t{self.construction_type}\t\t\t{self.boundary_previous}\t{self.boundary_post}"
        else:
            return f"{self.start}\t{self.end}\t{self.construction_type}\t\t{self.boundary_previous}\t{self.boundary_post}"

    def update_geometry(self, geo):
        """
        Function updates the way chain geometry to be the union of the way chain and geo
        :param geo: A new geometry
        :return: None
        """
        self.geometry = self.geometry.union(geo)

    @staticmethod
    def get_next_serial():
        """
        Returns next available serial number
        :return: A new serial number
        """
        current_serial = WayChain.serial_no
        WayChain.serial_no += 1
        return current_serial


class WayChainMap:
    """
    A data structure used to manipulate a collection of WayChains.
    """
    def __init__(self):
        """
        A constructor
        """
        self.map = {}

    def __str__(self):
        header = f"chain_id\tstart\t\tend\t\tconstruction_tag\tprevious_tag\tfinal_tag\n"
        body = [f"{k}\t"+str(self.map[k]) for k in self.map.keys()]
        return header + '\n'.join(body)

    def get_map_ways(self):
        """
        Returns the ids of the all the waychains in the map.
        :return: A list of ids in the entire map
        """
        ids = []
        for k in self.map.keys():
            ids += self.map[k].ids
        return ids

    def find_key(self, way_id):
        """
        Returns a map key of the newest added way chain that contains the way
        :param way_id: The way id of the way for which a way chain needs to be found
        :return: The key corresponding to the most recently added way chain containing way id
        """
        # A list of way chain serial numbers which contain way_id
        serial_no_list = []
        for chain_key in self.map.keys():
            if str(way_id) in chain_key:
                serial_no_list.append([chain_key, self.map[chain_key].serial_no])

        # get the most recent serial number (largest)
        serial_no_list.sort(key=lambda x: x[1])
        return serial_no_list[-1][0]

    def update_map(self, way_id, start=None, end=None, construction_type=None, prev=None, post=None, geo=None):
        """
        Updates the most recent waychain containing way_id
        :param way_id: A way_id whose chain needs to be updated
        :param start: A new start date
        :param end: A new end date
        :param construction_type: A new construction type
        :param prev: A new previous tag
        :param post: A new post tag
        :param geo: A new geometry
        :return: None
        """
        key = self.find_key(way_id)
        if start is not None:
            self.map[key].start = start
        if end is not None:
            self.map[key].end = end
        if construction_type is not None:
            self.map[key].construction_type = construction_type
        if prev is not None:
            self.map[key].boundary_previous = prev
        if post is not None:
            self.map[key].boundary_post = post
        if geo is not None:
            self.map[key].update_geometry(geo)

    def update_chain_key(self, way_id, new_id, is_prev=False):
        """
        Adds a new way new_id to the key of the way chain in the map containing way_id. Deletes the old way chain.
        :param way_id: A way whose chain needs a new way
        :param new_id: A new way to be added
        :param is_prev: A boolean when true means the new_id should be added to the front of the list.
        :return: None
        """
        # get the original key containing way_id
        old_key = self.find_key(way_id)
        # remove the serial number
        bare_old_key = old_key.split("-")[0]
        # create the new key
        if is_prev:
            new_key = f"{new_id}_" + bare_old_key
        else:
            new_key = bare_old_key + f"_{new_id}"
        # assign the same serial number
        new_key = new_key + "-" + str(self.map[old_key].serial_no)
        # transfer the old chain
        self.map[new_key] = self.map[old_key]
        self.map.pop(old_key)

    def increment_chain(self, id_in_chain, new_id, is_prev=False):
        """
        Creates a new link in the way chain which contains id_in_chain. Also appends new_id to corresponding way_chain.
        :param id_in_chain: A way id corresponding to a chain which needs a new link
        :param new_id: The id of a way to be added to a chain
        :param is_prev: A boolean when true means the new_id should be added to the front of the list.
        :return: None
        """
        self.update_chain_key(id_in_chain, new_id, is_prev=is_prev)
        self.map[self.find_key(new_id)].ids.append(new_id)

    def get_way_chain(self, way_id):
        """
        Returns a copy to the chain containing way_id
        :param way_id: An id of a chain
        :return: A copy of the chain containing way_id
        """
        return self.map[self.find_key(way_id)]

    def get_gdf(self):
        """
        Returns a gdf containing a row for each WayChain in the WayChainMap. Each row includes WayChain.start, WayChain.
        end, WayChain.construction_type, WayChain.previous_tag, WayChain.final_tag, and WayChain.geometry.
        :return: A geopandas GeoDataFrame containing the information in self.
        """
        def _generate_row(key):
            """
            Generates a row containing chain_id, geometry, start, end, construction_tag, previous_tag, final_tag for a
            given way_id.
            :param key: The way_id of a way which needs to be added to the dataframe
            :return: A row for a dataframe containing id, geometry
            """
            # find the correct key in the map
            minx, miny, maxx, maxy = self.map[key].geometry.bounds
            return [key, str(self.map[key].start), str(self.map[key].end), str(self.map[key].construction_type),
                    str(self.map[key].boundary_previous), str(self.map[key].boundary_post)], box(minx, miny, maxx, maxy)
        
        data_col_names = ['chain_id', 'start', 'end', 'constr_tag', 'prev_tag', "final_tag"]
        rows = []
        geometries = []
        # generate a row for the GeoDataFrame
        for k in self.map.keys():
            row, geometry = _generate_row(k)
            rows.append(row)
            geometries.append(geometry)
        # Create the GeoDataFrames
        gdf = gpd.GeoDataFrame(rows, columns=data_col_names, geometry=geometries)
        gdf = gdf.sort_values(by=['start', 'end'])
        gdf = gdf.reset_index(drop=True)
        if len(gdf.index) == 0:
            return None
        return gdf
