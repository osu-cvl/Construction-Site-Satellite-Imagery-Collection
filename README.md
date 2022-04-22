# Extracting Imagery of OpenStreetMap Construction Over Time
This repo contains the official code for the paper "A Framework for Semi-automatic Collection of Temporal Satellite Imagery for Analysis of Dynamic Regions" by Nicholas Kashani Motlagh, Aswathnarayan Radhakrishnan, Jim Davis, and Roman Ilin.

This project aims to extract construction information from a region of interest over time. The modules in this package 
use data from
OpenStreetMap to leverage information about the region. After information is extracted, multi-temporal RGB and/or NIR 
imagery is collected from Sentinel-2 or Planet.
This imagery spans the time that an OpenStreetMap "Way" (polygon) was under construction. If you would like to read more about
OpenStreetMap ways, you can checkout this [link](https://wiki.openstreetmap.org/wiki/Way).

This package was developed by  

    Nicholas Kashani Motlagh, Aswathnarayan Radhakrishnan, Jim Davis @ Ohio State University  
    {kashanimotlagh.1,radhakrishnan.39,davis.1719}@osu.edu  
    
    and  
    
    Roman Ilin @ AFRL/RYAP, Wright-Patterson AFB  
    rilin325@gmail.com  

Should you have any questions, the principal point-of-contact is Dr. Jim Davis. This package was modified on 2020-08-05.

## Prerequisites
First, you must install all dependencies. To use these modules, first download osmium-tool using the following 
instructions based on your operating system.  
### macOS
Install homebrew via this [link](https://brew.sh/).  
Install osmium-tool via `brew`:  

`brew install osmium-tool`

### Debian Linux  
Install osmium-tool via `apt`:

`sudo apt install -y osmium-tool`

### Other
If you are using a different distribution of Linux or Windows, you will first need to install some prerequisite libraries.
Check the [project repository](https://github.com/osmcode/osmium-tool) for detailed instructions to download and build libraries from source.  

If you are a Windows user, consider downloading the [Ubuntu shell for Windows 10](https://www.microsoft.com/en-us/p/ubuntu/9nblggh4msv6?activetab=pivot)
to make the process easier. If you do not have access to the windows store, the directions below include instructions to manually install.

<details>  
<summary>Ubuntu VM instructions for Windows</summary>

+ Manual install
  + Install the Ubuntu 20.04 distro from: https://docs.microsoft.com/en-us/windows/wsl/install-manual
  + In powershell run `Add-AppxPackage .\{downloaded file ending with appx}`
+ In powershell run `Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux`
+ Restart the computer
+ Open the Ubuntu application and setup an account
+ Run `sudo apt update`
+ Install osmium-tool with `sudo apt install -y osmium-tool`
+ Download miniconda (optional but preferred) from https://docs.conda.io/en/latest/miniconda.html#linux-installers (use `wget {link}`). 
  + Run `bash {name of the downloaded file}`.
  + Answer `yes` to all prompts.
  + After conda is installed, close the session and restart it. 
  + Run `conda --version` to verify that conda was successfully installed.
+ Add the `/home/{username}/.local/bin` to PATH with  
```echo "export PATH=\"/home/{username}/.local/bin:\$PATH\"" >> .bashrc```.  
+ Run `source .bashrc`.  
+ **Note**: You can access the Windows file system from the `/mnt` directory. For example, the Windows Users directory 
is located at `/mnt/c/Users/{user}`.
</details>
<br>

Check that osmium installed correctly with `osmium --version`  

Next, you will need to create an environment and install all dependencies using either Conda or pip using the instructions below.

### Conda  
If you do not have conda downloaded, refer to these links: 
[macOS](https://docs.conda.io/projects/conda/en/latest/user-guide/install/macos.html), 
[Linux](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html), 
[Windows](https://docs.conda.io/projects/conda/en/latest/user-guide/install/windows.html). 
If you are using Ubuntu on Windows, you have already installed conda in the previous step.

Next, run the following. **Note, osmium can only be installed through pip.**  

`conda config --append channels conda-forge`  
`conda create --name {env name} --file requirements_conda.txt python=3.7`  
`conda activate {env name}`   
`pip install osmium`

If you're using Conda you can skip the next step and directly run the Demo.

### Pip
If you are only using **pip**, then run

`sudo apt install python3-venv`  
`python3 -m venv {env name}` 

If on windows:  
`{env name}\Scripts\activate`  

If on macOS or Linux:  
`source {env name}/bin/activate`  

Then run  
`pip install -r requirements_pip.txt`  

### Demo
You are now equipped to run `demo.ipynb`. If you would like to step through the walk-through, run the command `jupyter lab` on the terminal from the root directory of this repository and open `demo.ipynb`.

### Acquiring History Files
To download a history file, you will need an OSM account.
This is free and quick to do. Simply navigate to the [registration page](https://www.openstreetmap.org/user/new). Once you have made an account, you can download history files
found [here](http://download.geofabrik.de). Make sure that you scroll to "Other Formats and Auxillary Files" and find the line containing
a crossed-out .osh.pbf history file. Click the link "internal server". Then click
"Login with you OpenStreetMap account" and enter credentials. After you are logged in, you will be able to download the 
previously crossed-out internal.osh.pbf history file.

### Creating Poly Files
Next, gather a .poly file containing the polygon coordinates of
the region of interest to search. The polygon defined in the .poly file should be contained in the history file. More 
information about .poly files can be found [here](https://wiki.openstreetmap.org/wiki/Osmosis/Polygon_Filter_File_Format).



## Usage
Gathering imagery of OpenStreetMap construction sites is split into two main tasks: constructing a GeoDataFrame of all 
construction sites and retrieving images which correspond to those construction sites.
A GeoDataFrame is a datatype from the geopandas module which represents a table of data for areas including the coordinates that define the area.
You can read more about GeoDataFrames [here](https://geopandas.org/reference/geopandas.GeoDataFrame.html).

## Step 1: Site Extraction
In order to gather imagery of OpenStreetMap construction sites, we must first create a GeoDataFrame using the following 
modules. `setup` will be used to create the necessary directories. 
Then, `extract_sites` will be used to create a GeoDataFrame of construction sites from an OpenStreetMap history file.

### Setup
The directory structure required for the extract_sites module is below.
```
temp/
    snapshots/
    
output/
   collection/
```
You can create this by running `python setup.py` from the commmand line. Or, you can run
```python
from setup import setup_directory
setup_directory()
```

### Obtaining GeoDataFrames
This module will record all construction sites that were under construction in between the
start and end window given in the arguments and save the file as a GeoDataFrame found in `output/collection/collection.shp`. 
If a construction site began or ended outside the window, but it was under construction inside the window,
it will appear in the GeoDataFrame with correct start and end dates. 

The GeoDataFrame will contain a row for each construction site observed. Each row has a unique "chain_id" identifier 
followed by a start date, end date, construction type, previous tag, final tag, and polygon coordinates which define a 
bounding box containing the construction shape.
 
To extract a GeoDataFrame of construction sites, run  
`python extract_sites.py -s <start_date: YYYY-MM-DD> -e <end_date: YYYY-MM-DD> --poly=<poly file> --region=<region_file> 
<optional: --keep-temp> <optional: --restrict-window> <optional: --save-wip>`   

`-s` or `--start` is the starting date of the search. The module will only find construction sites which were under 
construction on or after this date. The start date must be on or after 2015-06-22.

`-e` or `--end` is the ending date of the search. The module will only find construction sites which were under construction on or before this date.
The end date must be on or before 10 days from today's date.

`-p` or `--poly` is a poly file containing the a polygon in lat/long of the region to search over.

`-r` or `--region` is an OSM history file which contains the polygon you are searching over.

`--keep-temp` is a flag which when set will not delete all daily snapshots or completed site shape files recorded during
 the execution of the module. This flag should be used when you
would like to import a snapshot into GIS software such as QGIS to take a closer look at a construction site. (Default: False)

`--restrict-window` is a flag which when set will restrict the search to only the dates listed. That is, any site that
 was completed before the end date will appear in the `output/collection/collection.shp` file. Note that if a site has a
 start date which is the start date of the search, this may not be the true start date of construction; however, the end
 date will be correct. (Default: False)

`--save-wip` is a flag which when set will save the work-in-progress construction sites as a GeoDataFrame. This dataframe can
be found in `output/collection/in_progress.shp`. (Default: False)

For example, let's say we ran a search from 2015-06-23 to 2016-06-23.
If a construction site began on 2015-01-20 and ended on 2016-07-01, it will be extracted and recorded in 
`output/collection/collection.shp` with its corresponding start and end dates.

An info file for each construction site can be found at `output/{chain_id}/info.txt`. 
The file contains data from the GeoDataFrame as a comma separated list: `start_date,end_date,construction_type,previous_tag,final_tag,minx,miny,maxx,maxy` where minx, miny, maxx, maxy are the coordinates of the bounding box that contains the construction site.

If you would like to use this module in other programs, you can import the module and use it as follows
```python
import extract_sites
params = {} # Fill with parameter name:value pairs ("start":"2019-02-02", "end", "poly", "region"...)
extract_sites.set_params(params)

# Get GeoDataFrames of in-progress sites and complete sites
in_progress_gdf, collection_gdf = extract_sites.locate_construction()
# Create an info.txt file for each row of "complete" construction sites
extract_sites.create_dataset(collection_gdf)
```

Often times, you may want to run the script multiple times. To clear the directories that were created, simply run  
 `python reset_extract.py`  
 
 or
 
 ```python
import reset_extract
reset_extract.reset()
```

Please save the files in `output/` to another location before running reset because it will be deleted.

## Step 2: Image Gathering
To gather images of construction sites that were identified in the previous script, run

`python gather_images.py --source=<s or p> --num-images=(an int >= 3 or -1 for all images) --api=<API KEY>
<optional: --padding=int> <optional: --rgb> <optional: --nir> <optional: --verbose> <optional: --email> 
<optional: --download-planet> <optional: --verbose>`

`-s` or `--source` is the source from which the script will gather images. If you are using Sentinel-2 use 's', otherwise,
use 'p' for Planet.

`-n` or `--num-images` is the number of images you would like to gather for each construction site. Note that images are
gathered in even increments throughout construction including the start date and the end date. So, this value must be greater than or
equal to 3, or this value can be -1 if you would like to gather all images available in the construction window. (Default: 3)  

`--api` is the API Key for the source that you are using.

`-p` or `--padding` is the scale factor of the region you would like to capture an image for. By default this value is set to
1 so that only the bounding box around the construction site will be extracted. If you would like to extract a larger region around a construction site,
you can set this value to 2, for example, to get a bounding box whose area is twice as large as the bounding box which contains the construction: 
the width and height of the bounding box are scaled by sqrt(2).  
Note, the scaled bounding box is still center invariant. (Default: 1)  

`-C` or `--rgb` will gather images from the visible light bands. (Default: False)  

`-N` or `--nir` will gather images from the near infrared band. (Default: False)  

`--email` is used to receive email notifications when downloading from Planet. Planet will send an email notification to the address
registered with the API key when an order of imagery is ready for download. At least one order (sometimes more) will be created for each
site in a GeoDataFrame. (Default: False)  

`--download-planet` is used to download planet previously created orders. (Default: False)  

`--verbose` If set to true the module will print progress updates. (Default: False) 


This script will gather images from the listed source where `--source=s` corresponds to Sentinel-2 and `--source=p` corresponds to Planet.
The script will gather `--num-images` images in between the start and end date of construction, evenly divided (as best as possible).
If you'd like to acquire images with padding around the construction site, you can set a `--padding` value. This value 
will scale the bounding box while staying center invariant.
Add `--rgb` or `--nir` to select the bands to retrieve. Images of a certain construction site from a band (NIR/RGB)
will be saved in `output/{chain_id}/images/{source}/{rgb or nir}/`.

If you would like to use this module in other programs, you can import the module and use it as follows
```python
import gather_images
# Used to read in GeoDataFrame from collection file
import geopandas as gpd
# Used to create platform independent paths
from pathlib import Path

# Set parameters
params = {} # Fill with parameter name:value pairs ("source":"p", "num-images":3, "padding", "rgb"...)
gather_images.set_params(params)
# If you are using sentinel
gather_images.SENTINEL_INSTANCE_ID = ''
# If you are using planet
gather_images.PLANET_API_KEY = ''
# Get the GeoDataFrame of the collection file
collection_path = Path("output/collection/collection.shp")
collection_gdf = gpd.read_file(str(collection_path))
# Create the necessary directories
gather_images.setup()
# Get imagery
gather_images.gather_from_source(collection_gdf)
# Set download_planet to True to download imagery from planet.
gather_images.gather_from_source(collection_gdf, download_planet=True)
```
If you would like to clear all directories created by the `gather_images.py` simply run `python reset_images.py`
or  
```python
import reset_images
reset_images.reset()
```

#### Using Planet
Planet imagery is gathered in 2 steps: ordering and downloading.
* An order is placed for every site after 2017-02-19 (no images will be gathered for a site that began before that date).
* Planet imagery is sparse in 2017, but improves in more recent history.
* You can download an order some time after it is created.
* Each order can take between 5-15 minutes to download depending on the duration of construction.
* You can set the email parameter to true to receive an email every time an order is ready.

#### Using Sentinel
Sentinel imagery is gathered in one step. Imagery is gathered for every site on or after 2015-06-23 (no images will be gathered 
for a site that began before that date).  

In order to access imagery on sentinel hub, you must first create a new configuration on the sentinel dashboard found 
at https://apps.sentinel-hub.com/dashboard/#/configurations.

<details>  
<summary>Sentinel dashboard instructions</summary>
    
+ Click "New configuration"
+ Enter in a name
+ Select "Python scripts template" from the dropdown
+ Edit your configuration
+ Increase image quality to 100
+ Click "Add a new layer"
+ Name the new layer "NIR"
+ Select "B08"
+ Select "B08 - reflectance"
+ Click "Copy script to editor"
+ Click "Set custom script"
+ Adjust the cloud coverage to 100
+ Click "Save"

**Creating a new layer whose "ID" is "NIR" is vital here.** Parameters such as cloud coverage and atmospheric correction
 can be changed; however, we will leave these as is for the sake of this demo.
</details>  
  
### Output
RGB and NIR images will be saved as `output/{chain_id}/images/{source}/{rgb or nir}/{date_acquired}.png`.  

RGB images from planet will also contain a mask for faulty peripheral pixels saved as `output/{chain_id}/images/{source}/rgb/{date_acquired}_mask.png`.
In the RGB mask, all pixels marked with a 0 are faulty.  

NIR images from planet will come with an unusable data mask which will be saved as `output/{chain_id}/images/{source}/nir/{date_acquired}_udm.tif`. 
Check page 94 and 95 of https://assets.planet.com/docs/combined-imagery-product-spec-final-august-2019.pdf for more information on
UDM files.

In the case that all images are downloaded (`num-images` = -1), blank images will be saved for days which had no imagery. These images will be saved as
`output/{chain_id}/images/{source}/{rgb or nir}/{date_acquired}_empty.png`

## How it works
### Obtaining GeoDataFrames
The module first extracts a history file of the polygon passed in the arguments using osmium-tool. This history file will only contain ways
which were under construction at one point in time. 
The extract_sites module will then take daily snapshots from the start date to the end date. These snapshots are named
`temp/snapshots/{current date}-candid.osm`. From these daily snapshots, changes will be recorded. If a site
was under construction on the start date of the search window, extract_sites will travel backwards in time, only checking for changes in sites that
were under construction in the window. That is, any site that was not under construction in the specified time window will not
be recorded. Once all sites at the start of the window have a start date, the module will record changes in construction inside the window.
Once all construction changes inside the search window have been recorded, the module will search from the end of the window to 10 days before today's date
to see if the site was completed after the window. No new sites that are found after the window will be added to the GeoDataFrame.

In a GeoDataFrame, you will see columns chain_id, start, end, construction_type, prev_tag, final_tag, and geometry. The chain_id is a unique
id which contains all way ids in a "construction chain" (more on this later) followed by a unique serial number. The start column
is the date which construction was first observed. The end column is the last date which construction was observed. The construction
type is the tag which was labeled construction (either building or landuse). The prev_tag and final_tag columns are the estimated tags of
what the construction site was before and after construction, respectively. Note, these tags are just an estimate. The tag is computed
by checking the site under construction on boundary dates: either the day before construction started or the day after construction ended.
Any area that occupied the construction site on a boundary date is considered as a tag. All considered areas are sorted 
from largest to smallest by the intersection over union (IOU):

`area of intersection (with the construction site) / area of union (with the construction site)`

If there is a tie, the smallest considered area is chosen. However, the "chosen" areas must meet an (IOU) threshold. 
We call this `tag_confidence` in the code.
This tag confidence exists to omit areas which graze through the construction site and are not representative of the construction.
If a construction site has no previous or final tag, it is marked with "NO TAG FOUND". The `tag_confidence` value can be increased
for more confident tag values. However, note that a larger threshold results in less final tags in the resulting GeoDataFrame.

#### Example:
Consider a parking lot that was under construction. The parking lot was transformed into a park; however, the park was not marked
as an area on the day following construction. Instead, only a sidewalk was marked in the area. Because the side walk intersected the
construction area, we consider it. But, because it is unlikely that IOU score of the sidewalk and construction is high,
it is probably not chosen. Therefore, the final tag of the construction site would be marked as "NO TAG FOUND".

#### Construction Chains:
Not often, you will find that the final tag of a construction site will be another construction site. We call this special case
a "construction chain". In this special case,
we compare the IOU of the completed construction site with the new construction site against a confidence value called
 `construction_chain_confidence` in the code.
To prevent false positives, it is good practice to keep this value high. If the IOU falls below the confidence value, the new construction area
is discarded from the list of considered areas. This means that a final or previous tag will never be "construction".

At the end of the module, a GeoDataFrame will be saved containing the chain_id, start date, end date, construction type (either building or landuse),
the previous tag of the site, the final tag of the site, and a polygon bounding box containing the union of all changes to the site over the course of
its time spent under construction. 

#### Fetching Images
The number of images specified in the arguments to the `gather_images` module will be fetched. These images are fetched
as evenly as possible in between the start and end dates including the start date and the end date.
Sentinel-2 captures images every 5 days starting 2015-06-23, while Planet captures images daily after 2017-02-19. If an 
image is not available for a specific date,
the next available image is gathered (up to 5 days after).
Imagery will not be downloaded for construction sites whose start date falls before the source start date (2015-06-23 for
 Sentinel-2 and 2017-02-19 for Planet).

#### Example
The construction of a building took 40 days, and you would like to fetch 3 images. The first image fetched will be on the start date
(up to 5 days after). The next image fetched will be on day 20 of construction (up to 5 days after). And the final image fetched will be on
the last day of construction (up to 5 days after).

#### Tips

If you know which satellite imagery provider you will be using, set the start date of construction extraction to one day before the cut-off date
for that provider (2015-06-22 for Sentinel-2, 2017-02-18 for Planet). Also set `restrict-window` to True.
This will restrict the search window to only search for sites that were under construction the day before the cut-off date and no earlier.
Then, when imagery is collected, all sites that were under construction before the cut-off date will not be considered.

If you would like to download images for a GeoDataFrame not found in `output/collection/collection.shp`, you can pass the
GeoDataFrame like so
```python
gather_images.setup(other_gdf=my_data_frame)
...
gather_images.gather_from_source(my_data_frame)
```
Note that imagery will still be saved to `output`.
