import uuid
import pyproj
import math
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from shapely.ops import transform


def get_run_order(data, candidate_runs, rotation=-10):
    data = data[data.name.isin(candidate_runs)]
    ax = data.geometry.plot(figsize=(10, 10))
    for idx, row in data.iterrows():
        # Get the first point of the line segment (this assumes the geometry is a LineString)
        x_start = row.start.x
        y_start = row.start.y
        # Add the annotation text
        ax.text(x_start, y_start, row['id'], fontsize=8, ha='right', color='black', rotation=rotation)
    print("Not operational runs:", data[data.status!="operating"].name)
    print(data.id.unique())
    plt.show()


def combine_ski_runs(data, ordered_ids, new_name, difficulty, status):
    original_data = data.copy()
    data = runs[runs.id.isin(ordered_ids)]
    data_ordered = data.set_index('id').loc[ordered_ids].reset_index()
    run_id = data_ordered.id.iloc[0]
    ski_area_id = data_ordered.ski_area_id.iloc[0]
    connection_type = data_ordered.connection_type.iloc[0]
    distance = data_ordered["distance"].sum()
    duration = data_ordered.duration.sum()
    start_point = data_ordered.iloc[0].start
    end_point = data_ordered.iloc[0].end
    
    coordinates = []
    for idx, row in data_ordered.iterrows():
        coordinates.extend(list(row.geometry.coords))
    linestring = LineString(coordinates)

    new_entry = gpd.GeoDataFrame({"id": run_id,
                                    "name": new_name,
                                    "ski_area_id": ski_area_id,
                                    "connection_type": connection_type,
                                    "difficulty": difficulty,
                                    "distance": distance,
                                    "duration": duration,
                                    "geometry": linestring,
                                    "start": start_point,
                                    "end": end_point,
                                    "status": status}, index=[0])

    data_cleaned = original_data[~original_data.id.isin(ordered_ids)]
    data_cleaned = pd.concat([data_cleaned, new_entry])

    new_entry.geometry.plot()
    print("Runs before cleaning:", len(original_data))
    print("Runs after cleaning:", len(data_cleaned))

    return data_cleaned


def CreateBaseRunsLiftsGraph(points):
    """
    transform pandas dataframe to json of structure
    {'run_id': [{'point_id': '58ec74aa-fc4d-414e-94bd-82bc51cee7db',
        'connection_type': 'run',
        'distance': 4350.170313786595,
        'duration': 621.4529019695136,
        'difficulty': 'intermediate',
        'run_name': 'Grindel',
        'status': 'operating',
        'type': 'point',
        'point_coord': <POINT Z (647894.407 167976.609 2002)>},
        {}]
    }
    """
    RunsLiftsGraph = []
    run_tmp = []
    counter = 1

    for run_id, run_name, point_id, points_by_run, point_coord, connection_type, distance, duration, difficulty, status in list(zip(points.run_id, points["name"], points.point_id, points.points_by_run, points.geometry, points.connection_type, points["distance"], points.duration, points.difficulty, points["status"])):
        if counter < points_by_run:
            run_tmp.append({
                "point_id": point_id,
                "connection_type": connection_type,
                "distance": distance,
                "duration": duration,
                "difficulty": difficulty,
                "run_name": run_name,
                "status": status,
                "type": "point",
                "point_coord": point_coord
            })
            counter += 1

        elif counter == points_by_run:
            run_tmp.append({
                "point_id": point_id,
                "connection_type": connection_type,
                "distance": distance,
                "duration": duration,
                "difficulty": difficulty,
                "run_name": run_name,
                "status": status,
                "type": "point",
                "point_coord": point_coord
            })
            RunsLiftsGraph.append({run_id: run_tmp})

            run_tmp = []
            counter = 1

    return RunsLiftsGraph


def GetConnections(RunsLiftsGraph, points, custom_buffer, current_run_id=None, run_id_idx=0):
    """
    check for connections between runs and lifts and generate nodes
    loop through all points of runs THEN
    loop through all points of all runs (beside same run or already connected) and check if they are within buffer of start/end point
    """
    def replace_point_id(graph, old_id, new_id):
        for run in graph:
            for point in list(run.values())[0]:
                if point.get("point_id") == old_id:
                    point["point_id" ] = new_id
                    point["type" ] = "node"
        return graph

    replaced_ids = set()
    buffer_zone = 2

    for run_id, point_id_p, coords_p, difficulty_p, duration_p, connection_type_p, name_p, status_p in list(zip(points.run_id, points.point_id, points.geometry, points.difficulty, points.duration, points.connection_type, points["name"], points.status)):
        
        if run_id != current_run_id:
            current_run_id = run_id
            run_id_idx = 0
        else:
            run_id_idx += 1

            
        connected_points = []
        connected_runs = []

        for RunLift in RunsLiftsGraph:
            candidate_run_id = list(RunLift.keys())[0]

            # Skip same run or already connected
            if run_id == candidate_run_id or candidate_run_id in connected_runs:
                continue

            points_in_buffer = []
            for point in list(RunLift.values())[0]:
                distance_to_point = coords_p.distance(point.get("point_coord"))

                buffer_limit = custom_buffer.get(run_id, buffer_zone)

                # check if buffer_limit is a dict if True return value for index
                if type(buffer_limit) is dict:
                    buffer_limit = buffer_limit.get(str(run_id_idx), 2)

                if point_id_p != point.get("point_id") and distance_to_point <= buffer_limit:
                    points_in_buffer.append({
                        "point_id": point.get("point_id"),
                        "distance": distance_to_point
                    })

            # Get closest point in buffer, if any
            if points_in_buffer:
                closest_point = min(points_in_buffer, key=lambda p: p["distance"])
                connected_points.append(closest_point["point_id"])
                connected_runs.append(candidate_run_id)

        # Replace IDs only once per node
        if connected_points:
            node_id = str(uuid.uuid4())
            all_ids_to_replace = connected_points + [point_id_p]

            for match in all_ids_to_replace:
                if match not in replaced_ids:
                    replace_point_id(RunsLiftsGraph, match, node_id)
                    replaced_ids.add(match)

    return RunsLiftsGraph


def GetUnconnectedRunsLifts(Graph):
    unconnected_nodes = []

    for RunLift in Graph:
        run_lift_id = list(RunLift.keys())[0]
        body = list(RunLift.values())[0]

        for idx, point_item in enumerate(body):
            if point_item.get("type") != "node":
                if idx == 0:
                    location = 'start'
                elif idx == len(body) - 1:
                    location = 'end'
                else:
                    continue  # Skip if it's not the first or last point

                run_name = point_item.get("run_name")
                unconnected_nodes.append({run_lift_id: [run_name, location]})

    print("Unconnected start and end points:", len(unconnected_nodes))
    return unconnected_nodes


def CreateRunsLiftsGraphPoints(RunsLiftsGraph, epsg):
    """
    Generate RunsLiftsGraph as required by the UI
    """
    difficulty_to_color = {
        'lift': "#F1F10A",
        'advanced': '#000000',
        'intermediate': "#FF0000",
        'easy': '#0000FF',
        'novice': '#008000'
    }

    RunsLiftsGraph_tmp = {"type": "FeatureCollection"}
    features = []

    project = pyproj.Transformer.from_proj(
        pyproj.Proj(init=f'epsg:{epsg}'), # source
        pyproj.Proj(init='epsg:4326')) # destination

    for run in RunsLiftsGraph:

        feature = {"type": "Feature"}
        properties = {}
        geometry = {"type": "LineString"}
        coordinates = []
        point_ids = []
        run_id = list(run.keys())[0]
        points = list(run.values())[0]
        for point in points:
            coords_wgs = transform(project.transform, point.get("point_coord"))
            coordinates.append([coords_wgs.coords[0][0], coords_wgs.coords[0][1]]) # lon, lat
            point_ids.append(point.get("point_id"))

            # add nodes
            if point.get("type") == 'node':
                #print(points[0])
                point_feature = {
                        "type": "Feature",
                        "properties": {
                            "point_id": point.get("point_id")
                        },
                        "geometry": {
                            "coordinates": [
                            coords_wgs.coords[0][0],
                            coords_wgs.coords[0][1]
                            ],
                            "type": "Point"
                        }
                    }
                
                features.append(point_feature)

            else:
                continue


        geometry["coordinates"] = coordinates
        properties["run_id"] = run_id
        # replace run_name with Ski run if None
        if points[0].get("run_name") is None:
            properties["run_name"] = "Ski run"
        else:
            properties["run_name"] = points[0].get("run_name")
        properties["type"] = points[0].get("type")
        # replace difficulty with novice if None
        if points[0].get("difficulty") is None:
            properties["difficulty"] = "novice"
        else:
            properties["difficulty"] = points[0].get("difficulty")
        # replace status with unknown if None
        if points[0].get("status") is None:
            properties["status"] = "unknown"
        else:
            properties["status"] = points[0].get("status")
        # set stroke-width to 3 if run_name not 'Ski run'
        if points[0].get("run_name") == "Ski run":
            properties["stroke-width"] = 1
        else:
            properties["stroke-width"] = 3
        properties["duration"] = points[0].get("duration")
        properties["distance"] = points[0].get("distance")
        properties["point_id"] = point_ids
        properties["stroke"] = difficulty_to_color.get(properties.get("difficulty"))
        feature["properties"] = properties
        feature["geometry"] = geometry

        features.append(feature)

    RunsLiftsGraph_tmp["features"] = features

    return RunsLiftsGraph_tmp


def CreateRunsLiftsGraph(RunsLiftsGraph, epsg):
    """
    Generate RunsLiftsGraph as required by the UI
    """
    RunsLiftsGraph_tmp = {"type": "FeatureCollection"}
    features = []

    project = pyproj.Transformer.from_proj(
        pyproj.Proj(init=f'epsg:{epsg}'), # source
        pyproj.Proj(init='epsg:4326')) # destination

    for run in RunsLiftsGraph:

        feature = {"type": "Feature"}
        properties = {}
        geometry = {"type": "LineString"}
        coordinates = []
        point_ids = []
        run_id = list(run.keys())[0]
        points = list(run.values())[0]
        for point in points:
            coords_wgs = transform(project.transform, point.get("point_coord"))
            coordinates.append([coords_wgs.coords[0][0], coords_wgs.coords[0][1]]) # lon, lat
            point_ids.append(point.get("point_id"))

        geometry["coordinates"] = coordinates
        properties["run_id"] = run_id
        # replace run_name with Ski run if None
        if points[0].get("run_name") is None:
            properties["run_name"] = "Ski run"
        else:
            properties["run_name"] = points[0].get("run_name")
        properties["connection_type"] = points[0].get("connection_type")
        # replace difficulty with novice if None
        if points[0].get("difficulty") is None:
            properties["difficulty"] = "novice"
        else:
            properties["difficulty"] = points[0].get("difficulty")
        # replace status with unknown if None
        if points[0].get("status") is None:
            properties["status"] = "unknown"
        else:
            properties["status"] = points[0].get("status")
        properties["duration"] = points[0].get("duration")
        properties["distance"] = points[0].get("distance")
        properties["point_id"] = point_ids
        feature["properties"] = properties
        feature["geometry"] = geometry

        features.append(feature)

    RunsLiftsGraph_tmp["features"] = features

    return RunsLiftsGraph_tmp


def CreateTmpNodesGraph(RunsLiftsGraph, epsg):

    project = pyproj.Transformer.from_proj(
        pyproj.Proj(init=f'epsg:{epsg}'), # source
        pyproj.Proj(init='epsg:4326') # destination
    ) 
    
    RunsLiftsNodesGraph = []

    for RunLift in RunsLiftsGraph:
        first_point = True
        point_counter = 0
        run_coords = []
        run_coords_wgs = []
        run_tmp = []
        last_point = len(list(RunLift.values())[0])
        for point in list(RunLift.values())[0]:
            point_counter += 1

            if point.get("run_name") is None:
                run_name = "Ski run"
            else:
                run_name = point.get("run_name")
            
            # cache start point
            if first_point == True:
                start_tmp = {"point_id": point.get("point_id"),
                            "connection_type": point.get("connection_type"),
                            "distance": point.get("distance"),
                            "duration": point.get("duration"),
                            "difficulty": point.get("difficulty"),
                            "run_name": run_name,
                            "status": point.get("status"),
                            "type": point.get("type"),
                            "point_coord": point.get("point_coord"),
                            "coordinates": []} 


            #pointer_start = 1 # reset pointer
            run_coords.append(point.get("point_coord"))

            # reached next node or last point, calculate run length
            if (point.get("type") == "node" or point_counter == last_point) and first_point != True:
                for run_coord in run_coords:
                    coords_wgs = transform(project.transform, run_coord)
                    run_coords_wgs.append([coords_wgs.coords[0][0], coords_wgs.coords[0][1]]) # lon, lat

                length_segment = LineString(run_coords).length
                start_tmp["distance"] = length_segment 
                start_tmp["duration"] = point.get("duration") * (length_segment / point.get("distance"))
                start_tmp["distance_prop"] = length_segment / point.get("distance")
                start_tmp["coordinates"] = run_coords_wgs
                run_tmp.append(start_tmp)
                run_coords = [] # reset run
                run_coords_wgs = []
                run_coords.append(point.get("point_coord")) # set new start point
                start_tmp = {"point_id": point.get("point_id"),
                            "connection_type": point.get("connection_type"),
                            "distance": point.get("distance"),
                            "duration": point.get("duration"),
                            "difficulty": point.get("difficulty"),
                            "run_name": run_name,
                            "status": point.get("status"),
                            "type": point.get("type"),
                            "point_coord": point.get("point_coord")}
            else:
                first_point = False

            # add last point
            if point_counter == last_point:
                run_tmp.append({"point_id": point.get("point_id"),
                                "connection_type": point.get("connection_type"),
                                "duration": 0.0,
                                "distance": 0.0,
                                "difficulty": point.get("difficulty"),
                                "run_name": run_name,
                                "status": point.get("status"),
                                "type": "end",
                                "point_coord": point.get("point_coord"),
                                "distance_prop": 0.0,
                                "coordinates": []}) 

        # append modified run
        RunsLiftsNodesGraph.append({list(RunLift.keys())[0]: run_tmp})

    return RunsLiftsNodesGraph


def clean_connections(data):
    cleaned_data = []
    zero_distance_removed = 0

    for item in data:
        new_item = {}
        for key, connections in item.items():
            filtered_connections = []

            for conn in connections:
                # Remove if distance == 0.0 and not type == 'end'
                if conn['distance'] == 0.0 and conn.get('type') != 'end':
                    zero_distance_removed += 1
                    continue

                filtered_connections.append(conn)

            new_item[key] = filtered_connections
        cleaned_data.append(new_item)

    return cleaned_data, zero_distance_removed


def _to_edge(node, rund_id):
        # replace difficulty with novice if None
        if node.get("difficulty") is None:
            difficulty = "novice"
        else:
            difficulty = node.get("difficulty")

        edge = {
            "run_id": rund_id,
            "run_name": node.get("run_name"),
            "duration": node.get("duration"),
            "distance": node.get("distance"),
            "difficulty": difficulty,
            "distance_prop": node.get("distance_prop"),
            "coordinates": node.get("coordinates")
        }
        return edge

def _get_matching_nodes(graph, connections, node_id):

        for runlift in graph:
            body = list(runlift.values())[0]

            position_counter = 0
            n_nodes = len(body) - 1
            for node in body:
                # matching point_id, not last element of run
                if node.get("point_id") == node_id and position_counter < n_nodes:

                    edge = _to_edge(node, list(runlift.keys())[0])

                    #if node already added to connections
                    next_node_id = body[position_counter+1].get("point_id")
                    if next_node_id in list(connections.keys()):

                        # if duration new node shorter than duration existing note -> replace
                        if connections.get(next_node_id).get("duration") < edge.get("duration"):
                            continue

                        else:
                            connections[body[position_counter+1].get("point_id")] = edge
                        
                    else:
                        connections[body[position_counter+1].get("point_id")] = edge

                position_counter += 1
                
        return connections

def CreateNodesGraph(RunsLiftsNodesGraph):

    NodesGraph = []
    used_nodes = []

    for runlift in RunsLiftsNodesGraph:
        body = list(runlift.values())[0]

        for node in body:

            if node.get("point_id") not in used_nodes:
                connections = {}
                connections = _get_matching_nodes(RunsLiftsNodesGraph, connections, node.get("point_id"))

            
                NodesGraph.append({"node":
                                    {node.get("point_id"):
                                    {"connected_nodes": connections}}
                                    })
            used_nodes.append(node.get("point_id"))
            
    return NodesGraph


def getIncomingNodesCoords(node_graph, runslift_graph, main_node_id, lag=1):
    """
    # iterate through all nodes in NodeGraph
    for node_ in node_graph.get("features"):
        incoming_edge = {}
        main_node_id = list(node_.get("node").keys())[0]
    """
    
    incoming_edge = {}

    # iterate through all nodes to find where main_node is a connecting node -> incoming connection
    for node in node_graph.get("features"):

        # iterate through connected_nodes of each node
        for connected_node_id in list(list(node.get("node").values())[0].get("connected_nodes").keys()):
            connected_node = list(node.get("node").values())[0].get("connected_nodes").get(connected_node_id)

            # if main_node appears as connected_node of another main node -> incoming connection
            if main_node_id == connected_node_id:
                incoming_node_id = list(node.get("node").keys())[0]
                connected_node_run_id = connected_node.get("run_id")

                # iterate through all runs and lifts to find the ones where main_node is one of their points
                for runlift in runslift_graph.get("features"):

                    if runlift.get("properties").get("run_id") == connected_node_run_id:
                        
                        # enumerate through all points of run until main_node reached
                        for idx, point_id in enumerate(runlift.get("properties").get("point_id")):

                            if point_id == main_node_id:
                                # if matching point is not start point
                                if idx != 0:
                                    incoming_point_coords = runlift.get("geometry").get("coordinates")[idx - lag][:2]
                                    main_node_coords = runlift.get("geometry").get("coordinates")[idx][:2]
                                    vector_incoming = (main_node_coords[0] - incoming_point_coords[0], main_node_coords[1] - incoming_point_coords[1])
                                    incoming_edge[incoming_node_id] = vector_incoming
                                else:
                                    continue
                           
    return incoming_edge


def getOutgoingNodesCoords(node_graph, runslift_graph, main_node_id, lag=1):
    """
    # iterate through all nodes in NodeGraph
    for node_ in node_graph.get("features"):
        outgoing_edge = {}
        main_node_id = list(node_.get("node").keys())[0]
    """
    outgoing_edge = {}

    # iterate through all nodes to get connected_nodes of main_node
    for node in node_graph.get("features"):

        # if node is main_node
        if main_node_id == list(node.get("node").keys())[0]:

            # iterate through all connected nodes get connected_node_id, node body, and run_id
            for connected_node_id in list(list(node.get("node").values())[0].get("connected_nodes").keys()):
                connected_node = list(node.get("node").values())[0].get("connected_nodes").get(connected_node_id)
                connected_node_run_id = connected_node.get("run_id")

                # iterate through all runs and lifts to find the ones where main_node is one of their points
                for runlift in runslift_graph.get("features"):

                    if runlift.get("properties").get("run_id") == connected_node_run_id:
                        
                        # enumerate through all points of run until main_node reached
                        for idx, point_id in enumerate(runlift.get("properties").get("point_id")):

                            if point_id == main_node_id:
                                # if matching point is not last point get coordinates lag points before
                                if idx != len(runlift.get("properties").get("point_id")) - 1:
                                    outgoing_point_coords = runlift.get("geometry").get("coordinates")[idx + lag][:2]
                                    main_node_coords = runlift.get("geometry").get("coordinates")[idx][:2]
                                    vector_outgoing = (outgoing_point_coords[0] - main_node_coords[0], outgoing_point_coords[1] - main_node_coords[1])
                                    outgoing_edge[connected_node_id] = vector_outgoing
                                else:
                                    continue

    return outgoing_edge


def signed_angle(v1, v2):
    cross = v1[0] * v2[1] - v1[1] * v2[0]
    dot   = v1[0] * v2[0] + v1[1] * v2[1]
    return math.atan2(cross, dot)


def get_turn_direction(vector_in, vector_out):
    """
    straight_thresh_deg: treat turns smaller than this as 'Straight'
    Returns (angle_radians, direction_str).
    """
   
    # If either vector is zero‐length, we can't define a turn
    if vector_in == (0, 0) or vector_out == (0, 0):
        return 0.0, "Straight"

    angle = signed_angle(vector_in, vector_out)
    degree = math.degrees(angle)
    abs_degree = abs(degree)

    if abs_degree < 10:
        direction = "Straight"
    elif 10 <= degree < 30:
        direction = "Slightly Left"
    elif 30 <= degree < 100:
        direction = "Left"
    elif degree >= 100:
        direction = "Sharp Left"
    elif -30 < degree <= -10:
        direction = "Slightly Right"
    elif -100 < degree <= -30:
        direction = "Right"
    else:  # deg <= -100
        direction = "Sharp Right"

    return angle, direction