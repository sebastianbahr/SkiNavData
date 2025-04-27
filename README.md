# SkiNavData
This repository contains the code to create the input data and the data used by the SkiNav iOS app.

https://github.com/RoanCreed/SkiNav


## Data folder
The data folder saves the downlaoded runs, lifts, and ski area .json files from OpenSkiMap. They should be updated from time to time. Probably before every new ski season to reflect changes in lifts and runs.

## Models folder
Use the data_generator file to select a ski resort, perform all needed data transformation, and add it to the folder of available ski resorts.

## SkiResorts folder
Stores all ski resorts that are currently available in the app. They will be queried as a raw .json or .geojson file from the app using their remote URL. The structure of this folder is as follows:

```
SkiResorts/
├── SkiResortManifest.json
└── resortId/
    ├── RunsLiftsGraph_v1.2.geojson
    ├── RunsLiftsGraph_swapped_v1.2.geojson
    ├── NodeGraph_v1.2.json
└── resortId/
    ├── RunsLiftsGraph_v2.0.geojson
    ├── RunsLiftsGraph_swapped_v2.0.geojson
    ├── NodeGraph_v2.0.json
```

### SkiResortManifest.json
Contains information about the name of each ski resort as well as the most recent version of each of the files. It will be needed to construct the remote URL. ```URL(string: "\(baseURL)\(resortId)/RunsLiftsGraph_v\(RunsLiftsGraphVersion).geojson") ``` or ```URL(string: "\(baseURL)\(resortId)/NodesGraph_v\(NodesGraphVersion).geojson")```

### RunsLiftsGraph_v1.2.geojson
Contains the ID, name, meta data, and the geometry of each lift and run. 
```
{'type': 'FeatureCollection',
    'features': [{'type': 'Feature',
        'properties': {
            'run_id': '11effb194edfdc7596d7fbcc4d28fe2fa13dee65',
            'run_name': 'Cascades',
            'connection_type': 'lift',
            'difficulty': 'lift',
            'status': 'operating',
            'duration': 285.0,
            'point_id': ['427dc856-3809-442b-8ea1-936ac7e33d05',
                        '8a939c25-5ea3-4edc-82ac-e73603b2a0d6']},
        'geometry': {'type': 'LineString',
        'coordinates': [[45.29511930005519, 6.577488103315183, 2253.0],
                        [45.29113160005627, 6.594552603310526, 2558.0]]}}
    ]
}
```
### RunsLiftsGraph_swapped_v1.2.geojson
Contains the same information than RunsLiftsGraph_v1.2.geojson the only difference is than latitude and longitude are swapped, as this is needed for Mapbox.

### NodeGraph_v1.2.json
Contains the each node and all nodes it is connected with including the duration to these nodes and the difficulte of the run. The data is needed for AStar. 
```
{'features': [
    {'node': 
        {'427dc856-3809-442b-8ea1-936ac7e33d05': 
            {'connected_nodes': 
                {'8a939c25-5ea3-4edc-82ac-e73603b2a0d6': 
                    {'duration': 285.0,
                    'difficulty': 'lift',
                    'distance_prop': 0.9999999971843626}}}}},
    {'node': 
        {'8a939c25-5ea3-4edc-82ac-e73603b2a0d6': 
            {'connected_nodes': {'e054bea2-4ef5-47ac-aa15-de3214bb0f4c':
                {'duration': 196.07908956605502,
                'difficulty': 'novice',
                'distance_prop': 0.014525672629369888}}}}},
    ]
}
```