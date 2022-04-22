"""
This module contains a function which will delete all files and directories created in the gather_images module.
"""

__author__ = """Nicholas Kashani Motlagh @ Ohio State University\n
                Aswathnarayan Radhakrishnan @ Ohio State University\n
                Jim Davis @ Ohio State University (Point of Contact, see __email__)\n
                Roman Ilin @ AFRL/RYAP, Wright-Patterson AFB"""
__email__ = 'davis.1719@osu.edu'
__date__ = "2020-08-05"

# Built-in/Generic Imports
import shutil
from pathlib import Path


def reset():
    """
    Will clear all directories and files made by gather_images.py and delete the directories created for each band.
    :return:
    """
    output_dir = Path("output")
    for f in output_dir.glob("*"):
        if "collection" in str(f):
            continue
        for i in f.glob("images/*"):
            if i.is_dir():
                shutil.rmtree(str(i))
            else:
                i.unlink()


if __name__ == "__main__":
    reset()
