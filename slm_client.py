import json
import urllib.request
import time
# define System prompt
# ChatGPT are used for help writing each field's description. 
SYSTEM_PROMPT = """
    You are a decision-maker for a drone.
    Input JSON fields:
    state: the drone's current state.
    state.position: the drone's current position in NED coordinates (north, east, down) and yaw in degrees.
    state.battery: Remaining battery as a fraction from 0 to 1.

    mission: the drone's mission parameters and progress.
    mission.cruise_alt: Desired altitude above the local origin, in meters.
    mission.waypoint_radius: Distance threshold for reaching a waypoint, in meters.
    mission.battery_low_threshold: Low battery threshold, expressed as a fraction from 0 to 1.
    mission.battery_critical_threshold: the battery level below which the drone should land immediately.
    mission.waypoint_index: the index of the next waypoint to visit, as a zero-based index into mission.waypoints.
    mission.waypoints: a list of waypoints, each with an id and NED coordinates.
    Each waypointentry contains:
         id: the waypoint identifier.
         north: north position in meters.
         east: east position in meters.
         down: down position in meters.

    Given the current state of the drone, you must choose one of the following actions: 
        "continue_waypoint", and "hover"
    
    Rules need to follow for choosing actions:
    1. If state.battery <= mission.battery_low_threshold, return action "hover" with waypoint_id null.
    2. Otherwise, if mission.waypoint_index < len(mission.waypoints), return action "continue_waypoint" with waypoint_id set to the id of the next waypoint in mission.waypoints.
    3. Otherwise, return action "hover" with waypoint_id null.
    If battery <= 0.2, choose hover. 
    also, specify the reason for your decision in the "reason" field.

    Return only JSON and only the required fields are accepted, Do not include ungiven fields.
)
"""
# define output format for the model
OUTPUT_FORMAT = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["continue_waypoint", "hover"],
        },
        "waypoint_id": {"type": ["string", "null"]},
    },
    "required": ["action", "waypoint_id"],
}
init_start = time.perf_counter()
opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({})
)
init_ms = (time.perf_counter() - init_start) * 1000
print(f"HTTP client initialization in {init_ms:.2f} ms")


# define a function to query the SLM model with the given input
# in this case, we use localhost Ollama API endpoint, but it can be changed to any other endpoint
def query_slm(model_input: dict) -> dict:
    payload = {
        "model": "qwen3.5:0.8b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(model_input)},
        ],
        "format": OUTPUT_FORMAT,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0,
            "num_ctx": 2048,
            "num_predict": 128,
        },
        "keep_alive": "10m",

    }

    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with opener.open(request) as response:
        return json.load(response)
