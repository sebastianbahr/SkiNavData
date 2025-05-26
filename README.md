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
                    {'run_id': '40256b966978648e2e1014ebe2130d0811c472f6',
                    'run_name': 'Firstbahn 2',
                    'duration': 179.9957844773598,
                    'distance': 889.0098287011313,
                    'difficulty': 'lift',
                    'distance_prop': 0.9999765804297766,
                    'incoming_nodes': {
                        '8a939c25-5ea3-4edc-82ac-e73603b2a456': 'straight',
                        '94tg6c25-5ea3-4edc-82ac-e73603b2a0d6': 'left'
                    }}}}}}},
    {'node': 
        {'8a939c25-5ea3-4edc-82ac-e73603b2a0d6': 
            {'connected_nodes': {'e054bea2-4ef5-47ac-aa15-de3214bb0f4c':
                {'run_id': '7da9c2cee5f8995b173ff0e890a0bf9495361c0d',
                'run_name': None,
                'duration': 10.675728581948984,
                'distance': 74.73010007364289,
                'difficulty': 'easy',
                'distance_prop': 0.7057238142152766,
                'incoming_nodes': {}}}}}},
    {'node': 
        {'92034fd4-5ea3-4edc-82ac-e73603b2a0d6': 
            {'connected_nodes': {}}}},
    ]
}
```

### Data processing steps
#### Data cleaning runs
* Remove runs with no elevation profile
* Remove runs with difficulty level not in novice, easy, intermediate, or advanced
* Remove runs that are not downhill
* If runs have no name but just a number call them 'Ski run ```digit```'
* Perform manuall data cleaning:
    - join runs that belong together
    - rename runs with generic run names
    - add changes to runs_changes.txt 

#### Data cleaning lifts