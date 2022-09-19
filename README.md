# Set up script to build JSON and JS files

## Description

This script does two things:

- Converts shapefiles into GeoJSONs (needed to plot them on the web map).
- Builds the JavaScript files needed for the timeseries charts.

## Docker Compose

The environment is prepared using a Docker container.

Install Docker Compose following the instructions at https://docs.docker.com/compose/install/.

## Clone the code

Clone this repository to your computer.

## Prepare the data

There are two input folders in the cloned code:

- `app/data`. The script will take every shapefile in this folder and will convert it into a GeoJSON file. These files are the ones used to plot the features on the map and there should be one shapefile/GeoJSON for each layer in the table of contents of the app.
- `app/timeseries`. Then, it will take every file in this folder to build the JavaScript files (`timeseriesData.js` and its equivalent `tcedata.js`).

Place the files accordingly. There a little more information on the README.md file in each of these folders.

## Run the script

```
docker-compose run all
```

All output files will be placed in the `output` folder.

When running the previous command you should exect an output similar to the following one:

```
Creating timeseries_all_run ... done

*******************************************************************
* WARNING: Output folder contains files, they may be overwritten. *
*******************************************************************
Do you want to proceed?(y/n) y

**************************************************
* Reading data folder and creating GeoJSON files *
**************************************************
Converting data/CIS_2000_prj.shp >>> CIS_2000_prj.json
Converting data/TCE_SW.shp >>> TCE_SW.json
Converting data/VC_SW.shp >>> VC_SW.json
Converting data/CIS_GW.shp >>> CIS_GW.json
Converting data/TCE_SW_prj.shp >>> TCE_SW_prj.json
Converting data/TCE_2000_prj.shp >>> TCE_2000_prj.json
Converting data/TCE_GW.shp >>> TCE_GW.json
Converting data/VC.shp >>> VC.json
Converting data/TCE_GW_prj.shp >>> TCE_GW_prj.json
Converting data/PCE.shp >>> PCE.json
Converting data/VC_prj.shp >>> VC_prj.json
Converting data/VC_SW_prj.shp >>> VC_SW_prj.json
Converting data/PCE_prj.shp >>> PCE_prj.json
Converting data/CIS_2000.shp >>> CIS_2000.json
Converting data/TCE_2000.shp >>> TCE_2000.json
Converting data/CIS_GW_prj.shp >>> CIS_GW_prj.json

***************************************************
* Reading timeseries folder and creating JS files *
***************************************************
Reading timeseries/TCE_SW.shp
Read 1256 rows (1256 total)
Reading timeseries/VC_SW.shp
Read 1257 rows (2513 total)
Reading timeseries/CIS_GW.shp
Read 8146 rows (10659 total)
Reading timeseries/TCE_GW.shp
Read 9522 rows (20181 total)
Reading timeseries/VC.shp
Read 9118 rows (29299 total)
Reading timeseries/PCE.shp
Read 8357 rows (37656 total)

Saving timeseriesData.js
Saving tcedata.js

************
* Finished *
************
```