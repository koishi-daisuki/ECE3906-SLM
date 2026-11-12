from tree import Current

def make_model_input(current: Current) -> dict:
    return {
        "state":{
            "position": {
                "north": current.north,
                "east": current.east,
                "down": current.down,
                "yaw": current.yaw
            },
            "battery": current.battery,
        },
        "mission":{
            "cruise_alt": current.cruise_alt,
            "waypoint_radius": current.waypoint_radius,
            "battery_low_threshold": current.battery_low_threshold,
            "battery_critical_threshold": current.battery_critical_threshold,
            "waypoint_index": current.waypoint_index,
            "waypoints": [
                {"id": name, "north": north, "east": east, "down": down}
                for name, north, east, down in current.waypoints
            ],
        }
        


    }