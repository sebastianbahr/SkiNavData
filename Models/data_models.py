import uuid
import pyproj
from shapely.geometry import LineString
from shapely.ops import transform

def CreateBaseRunsLiftsGraph(points):
    # create runsliftsgraph
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


def GetConnections(RunsLiftsGraph, start_end_points):
    def replace_point_id(graph, old_id, new_id):
        for run in graph:
            for point in list(run.values())[0]:
                if point.get("point_id") == old_id:
                    point["point_id" ] = new_id
                    point["type" ] = "node"
        return graph

    buffer_zone = 2

    for run_id, point_id_se, point_type_se, coords_se, difficulty_se, duration_se, connection_type_se, name_se, status_se in list(zip(start_end_points.run_id, start_end_points.point_id, start_end_points.point_type, start_end_points.geometry, start_end_points.difficulty, start_end_points.duration, start_end_points.connection_type, start_end_points["name"], start_end_points.status)):
        matching_runs = []
        connected_runs = []
        for RunLift in RunsLiftsGraph:
            points_in_buffer = []
            candidate_run_id = list(RunLift.keys())[0]
            # exclude points on same run
            if run_id != candidate_run_id and candidate_run_id not in connected_runs: 
                for point in list(RunLift.values())[0]:
                    distance_to_point = coords_se.distance(point.get("point_coord"))
                    if point_id_se != point.get("point_id") and distance_to_point <= buffer_zone:
                        points_in_buffer.append({"point_id": point.get("point_id"),
                                                "distance": distance_to_point})
                            
                # find closest point within buffer zone of specific run 
                Min = 10000
                for point_buffer in points_in_buffer:
                    if point_buffer.get("distance") < Min:
                        Min = point_buffer.get("distance")
                        point_id = point_buffer.get("point_id")

                if len(points_in_buffer) > 0:
                    matching_runs.append(point_id) # append matches
                    connected_runs.append(candidate_run_id)

        # replacing matching points with new node id
        if len(matching_runs) > 0: # matches found
            node_id = str(uuid.uuid4())
            # replace matching points id
            for match in matching_runs:
                replace_point_id(RunsLiftsGraph, match, node_id)
            # replace start/end point id
            replace_point_id(RunsLiftsGraph, point_id_se, node_id)

    return RunsLiftsGraph


def CreateRunsLiftsGraph(RunsLiftsGraph):
    RunsLiftsGraph_tmp = {"type": "FeatureCollection"}
    features = []

    project = pyproj.Transformer.from_proj(
        pyproj.Proj(init='epsg:27561'), # source
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
            coordinates.append([coords_wgs.coords[0][1], coords_wgs.coords[0][0], coords_wgs.coords[0][2]])
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
        properties["point_id"] = point_ids
        feature["properties"] = properties
        feature["geometry"] = geometry

        features.append(feature)

    RunsLiftsGraph_tmp["features"] = features

    return RunsLiftsGraph_tmp


def CreateRunsLiftsNodesGraph(RunsLiftsGraph):
    RunsLiftsNodesGraph = []

    for RunLift in RunsLiftsGraph:
        first_point = True
        point_counter = 0
        run_coords = []
        run_tmp = []
        last_point = len(list(RunLift.values())[0])
        for point in list(RunLift.values())[0]:
            point_counter += 1
            
            # cache start point
            if first_point == True:
                start_tmp = {"point_id": point.get("point_id"),
                            "connection_type": point.get("connection_type"),
                            "distance": point.get("distance"),
                            "duration": point.get("duration"),
                            "difficulty": point.get("difficulty"),
                            "run_name": point.get("run_name"),
                            "status": point.get("status"),
                            "type": point.get("type"),
                            "point_coord": point.get("point_coord")} 


            #pointer_start = 1 # reset pointer
            run_coords.append(point.get("point_coord"))

            # reached next node or last point, calculate run length
            if (point.get("type") == "node" or point_counter == last_point) and first_point != True:
                length_segment = LineString(run_coords).length
                start_tmp["distance"] = length_segment 
                start_tmp["distance_prop"] = length_segment / point.get("distance")
                run_tmp.append(start_tmp)
                run_coords = [] # reset run
                run_coords.append(point.get("point_coord")) # set new start point
                start_tmp = {"point_id": point.get("point_id"),
                            "connection_type": point.get("connection_type"),
                            "distance": point.get("distance"),
                            "duration": point.get("duration"),
                            "difficulty": point.get("difficulty"),
                            "run_name": point.get("run_name"),
                            "status": point.get("status"),
                            "type": point.get("type"),
                            "point_coord": point.get("point_coord")}
            else:
                first_point = False

            # add last point
            if point_counter == last_point:
                run_tmp.append({"point_id": point.get("point_id"),
                                "connection_type": point.get("connection_type"),
                                "distance": 0.0,
                                "difficulty": point.get("difficulty"),
                                "run_name": point.get("run_name"),
                                "status": point.get("status"),
                                "type": "end",
                                "point_coord": point.get("point_coord"),
                                "distance_prop": 0.0}) 

        # append modified run
        RunsLiftsNodesGraph.append({list(RunLift.keys())[0]: run_tmp})

    return RunsLiftsNodesGraph


def CreateNodesGraph(RunsLiftsNodesGraph):
    def to_edge(node):
        # replace difficulty with novice if None
        if node.get("difficulty") is None:
            difficulty = "novice"
        else:
            difficulty = node.get("difficulty")

        edge = {
            "duration": node.get("duration"),
            "difficulty": difficulty,
            "distance_prop": node.get("distance_prop")
        }
        return edge


    def get_matching_nodes(graph, connections, node_id):
        for runlift in graph:
            runlift = list(runlift.values())[0]

            position_counter = 0
            n_nodes = len(runlift)-1
            for node in runlift:
                # matching point_id, not last element of run, and not already appended
                if node.get("point_id") == node_id and position_counter < n_nodes: # and node.get("point_id") not in used_nodes
                    connections[runlift[position_counter+1].get("point_id")] = to_edge(node)

                position_counter += 1
                
        return connections


    NodesGraph = []

    for RunLift in RunsLiftsNodesGraph:
        nodes = list(RunLift.values())[0]

        for node in nodes:
            connections = {}
            connections = get_matching_nodes(RunsLiftsNodesGraph, connections, node.get("point_id"))
            NodesGraph.append({"node":
                                {node.get("point_id"):
                                    {"connected_nodes": connections}}
                                })
            #NodesGraph[node.get("point_id")] = connections
            #used_nodes.append(node.get("point_id"))
    return NodesGraph
