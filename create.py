import fiona
import json
import pathlib


def header(title):
    print()
    print("*" * (len(title) + 4))
    print(f"* {title} *")
    print("*" * (len(title) + 4))


def save_to(content, filename):
    print(f"Saving {filename}")
    with open(f"output/{filename}", "w") as output:
        output.write(content)


def process_data():
    header("Reading data folder and creating GeoJSON files")
    for filename in pathlib.Path('data').glob('*.shp'):
        output_name = str(filename).replace("data/", "").replace(".shp", ".json")
        print(f"Converting {filename} >>> {output_name}")
        geojson = to_geojson(filename)
        save_to(json.dumps(geojson), output_name)


def process_timeseries():
    header("Reading timeseries folder and creating JS files")
    data = []
    for filename in pathlib.Path('timeseries').glob('*.shp'):
        print("Gathering data from", filename)
        file_data = to_timeseries(filename)
        data = data + file_data
        print(f"Added {len(file_data)} rows.")

    # Sort the entire result by date.
    data.sort(key=lambda i: i.get('date'))

    result = {
        "timeseriesData": data
    }

    # Output JavaScript files
    print()
    print(f"Gathered {len(data)} rows from all files.")
    save_to(
        f"export default {json.dumps(result)};",
        "timeseriesData.js"
    )
    save_to(
        f"var tcedata = {json.dumps(data)};",
        "tcedata.js"
    )


class MissingData(Exception):
    pass


def to_geojson(filename):
    file = fiona.open(filename)
    features = []
    for feature in file:
        props = feature.get('properties')

        data = {
            'Well_ID': props.get('Well_ID', props.get('SWLOC_ID')),
            'SDate': props.get('SDate'),
            'Result': props.get('Result'),
            'Lab_Flag': props.get('Lab_Flag'),
            'Units': props.get('Units'),
            'X_Coord': props.get('X_Coord'),
            'Y_Coord': props.get('Y_Coord'),
        }

        if not all(data):
            raise MissingData(
                'Missing some of the fields on {}'.format(json.dumps(data))
            )

        features.append({
            "type": "Feature",
            "properties": data,
            "geometry": feature.get("geometry")
        })

    file.close()

    return {
        "type": "FeatureCollection",
        "features": features
    }


def to_timeseries(filename):
    file = fiona.open(filename)
    json = []
    for feature in file:
        props = feature.get('properties')
        # Get the required data with the required names
        data = {
            'date': props.get('SDate'),
            'close': props.get('Result'),
            'Matrix': props.get('Matrix'),
            'Analyte': props.get('Analyte'),
            'Well_ID': props.get('Well_ID', props.get('SWLOC_ID'))
        }

        if not all(data):
            raise MissingData(
                'Missing some of the fields on {}'.format(json.dumps(data))
            )

        json.append(data)
    return json


if __name__ == '__main__':
    proceed = False

    try:
        pathlib.Path('output').mkdir(mode=0o777, exist_ok=False)
        print("Creating app/output folder")
        proceed = True

    except FileExistsError:
        num_files = sum([1 if str(file) != "output/README.md" else 0
                         for file in list(pathlib.Path('output').iterdir())])
        if (num_files > 0):
            header("WARNING: Output folder contains files, they may be overwritten.")
            answer = input("Do you want to proceed?(y/n) ")
            if answer in ["y", "yes"]:
                proceed = True
            else:
                print("Stopping the process. Clear the folder and try again.")
        else:
            proceed = True

    except Exception as error:
        header(f"ERROR: Unkown error. {str(error)}")

    if proceed:
        process_data()
        process_timeseries()
        header("Finished")