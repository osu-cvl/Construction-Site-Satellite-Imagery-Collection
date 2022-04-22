"""
This module contains a function that can create new directories used in the extract_sites module.
"""

__author__ = """Nicholas Kashani Motlagh @ Ohio State University\n
                Aswathnarayan Radhakrishnan @ Ohio State University\n
                Jim Davis @ Ohio State University (Point of Contact, see __email__)\n
                Roman Ilin @ AFRL/RYAP, Wright-Patterson AFB"""
__email__ = 'davis.1719@osu.edu'
__date__ = "2020-08-05"

# Built-in/Generic Imports
from pathlib import Path


def setup_directory():
    """
    Create
    temp/
        snapshots/
    output/
        collection/
    :return: None
    """
    temp_path = Path("temp")
    snapshot_path = temp_path / "snapshots"
    output_path = Path("output")
    collection_path = output_path / "collection"
    if not temp_path.is_dir():
        temp_path.mkdir()
    if not snapshot_path.is_dir():
        snapshot_path.mkdir()
    if not output_path.is_dir():
        output_path.mkdir()
    if not collection_path.is_dir():
        collection_path.mkdir()


if __name__ == "__main__":
    setup_directory()
