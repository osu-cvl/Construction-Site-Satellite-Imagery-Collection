"""
This module contains a function which will delete all files and directories created in the extract_sites module.
"""

__author__ = """Nicholas Kashani Motlagh @ Ohio State University\n
                Aswathnarayan Radhakrishnan @ Ohio State University\n
                Jim Davis @ Ohio State University (Point of Contact, see __email__)\n
                Roman Ilin @ AFRL/RYAP, Wright-Patterson AFB"""
__email__ = 'davis.1719@osu.edu'
__date__ = "2020-08-05"

# Built-in/Generic Imports
import os
from pathlib import Path
import shutil


def reset():
    """
    Resets temp/ such that it only contains snapshots/ and completed_sites/.
    Resets output/ such that it only contains collection/.
    Deletes the outputpoly.osh.pbf file.
    :return:
    """
    snapshots_paths = Path("temp/snapshots")
    # delete all snapshots
    for snapshot in snapshots_paths.glob("*"):
        snapshot.unlink()
    #  delete all dirs in output except collection dir
    output_path = Path("output")
    collection_path = output_path / "collection"
    for output in output_path.glob("*"):
        if "collection" in output.parts:
            continue
        if output.is_dir():
            shutil.rmtree(str(output))
        else:
            output.unlink()

    # Delete all files in collection
    for collection in collection_path.glob("*"):
        collection.unlink()
    # Delete output poly
    if os.path.isfile("outputpoly.osh.pbf"):
        os.remove("outputpoly.osh.pbf")


if __name__ == "__main__":
    reset()
