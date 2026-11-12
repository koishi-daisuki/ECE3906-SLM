import math
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

import py_trees
from py_trees.common import Status


# name, meters north, meters east, meters down - (offboard mode measures down not up)
Waypoint = Tuple[str, float, float, float]


@dataclass
class Command:
    # Command type (none, position, velocity, hover, land)
    command_type: str = "none"

    # the desired position in the NED frame
    north: float = 0.0    # North coordinate in the NED frame
    east: float = 0.0     # East coordinate in the NED frame
    down: float = 0.0     # Down coordinate in the NED frame
    yaw: float = 0.0      # Yaw angle in the NED frame


@dataclass
class Current:
    # --- Current state of drone ---
    north: float = 0.0    # North coordinate in the NED frame
    east: float = 0.0     # East coordinate in the NED frame
    down: float = 0.0     # Down coordinate in the NED frame
    yaw: float = 0.0      # Yaw angle in the NED frame
    battery: float = 1.0  # Battery level (0.0 - 1.0)

    # --- Mission info ---
    cruise_alt: float = 5.0  # Cruise altitude
    waypoint_radius: float = 0.6  # radius around waypoint for it to be "reached"
    # Battery level threshold for low battery warning
    battery_low_threshold: float = 0.2
    # Battery level threshold for critical battery warning
    battery_critical_threshold: float = 0.1
    waypoints: List[Waypoint] = field(default_factory=lambda: [
        ("origin", 0.0, 0.0, 0.0),
        ("A", 5.0, 5.0, -5.0),
        ("B", 10.0, 10.0, -5.0),
        ("C", 0.0, 10.0, -5.0),
        ("D", 10.0, 0.0, -5.0),
    ])
    waypoint_index: int = 0
    command: Command = field(default_factory=Command)

    @property
    def altitude(self) -> float:
        # Returns the altitude of the drone in meters above the ground
        return -self.down

    def distance_to_waypoint(self, north: float, east: float) -> float:
        # Returns the distance to the waypoint in the horizontal plane
        return math.hypot(self.north-north, self.east-east)

    def distance_to_waypoint_3d(self, north: float, east: float, down: float) -> float:
        # Returns the distance to the waypoint in 3D space
        return math.sqrt((self.north - north) ** 2 + (self.east - east) ** 2 + (self.down - down) ** 2)


# ------------------------- Leaves
class Condition(py_trees.behaviour.Behaviour):
    def __init__(self, name: str, current: Current, function: Callable[[Current], bool]):
        super().__init__(name)
        self.current = current
        self.function = function

    def update(self) -> Status:
        return Status.SUCCESS if self.function(self.current) else Status.FAILURE


class Action(py_trees.behaviour.Behaviour):
    def __init__(self, name: str, current: Current, function: Callable[[Current], Status]):
        super().__init__(name)
        self.current = current
        self.function = function

    def update(self) -> Status:
        return self.function(self.current)


# ------------------------- Conditions
def battery_critical(
    current): return current.battery <= current.battery_critical_threshold


def battery_low(
    current): return current.battery <= current.battery_low_threshold
def mission_complete(current): return current.waypoint_index >= len(
    current.waypoints)


def has_waypoint(current): return not mission_complete(current)


def needs_takeoff(current):
    return (current.waypoint_index == 0 and has_waypoint(current) and current.altitude < current.cruise_alt)


# ------------------------- Actions
def act_takeoff(current):
    current.command = Command("takeoff")
    return Status.RUNNING


def act_return_home(current):
    if current.distance_to_waypoint(0, 0) < current.waypoint_radius:
        current.command = Command("land")
    else:
        current.command = Command(
            "position", 0, 0, -current.cruise_alt, current.yaw)
    return Status.RUNNING


def act_land(current):
    current.command = Command("land")
    return Status.RUNNING


def act_goto_waypoint(current):
    # go to the next waypoint on the list

    _, north, east, down = current.waypoints[current.waypoint_index]
    # if you are at the waypoint, increase index
    if current.distance_to_waypoint_3d(north, east, down) < current.waypoint_radius:
        current.waypoint_index += 1
        # if you are at the end of the waypoint list, hover in place
        if current.waypoint_index >= len(current.waypoints):
            current.command = Command("hover", yaw=current.yaw)
            return Status.SUCCESS
        _, north, east, down = current.waypoints[current.waypoint_index]
        # if you are not at the waypoint, calculate the yaw to face it
    if current.distance_to_waypoint(north, east) > current.waypoint_radius:
        yaw = math.degrees(math.atan2(east-current.east, north-current.north))
    # if you are at the waypoint but wrong height
    else:
        yaw = current.yaw
    current.command = Command("position", north, east, down, yaw)
    return Status.RUNNING


def act_hover(current):
    current.command = Command("hover", yaw=current.yaw)
    return Status.RUNNING


def build_tree(current: Current) -> py_trees.trees.BehaviourTree:
    def Cond(name, function): return Condition(name, current, function)
    def Act(name, function): return Action(name, current, function)

    # set up the tree
    Seq = lambda name, * \
        kids: py_trees.composites.Sequence(
            name, memory=False, children=list(kids))

    root = py_trees.composites.Selector("root", memory=False, children=[
        # 1. safety checks
        Seq("critical", Cond("battery_critical",
            battery_critical), Act("land", act_land)),
        Seq("low_battery", Cond("battery_low", battery_low),
            Act("return_home", act_return_home)),

        # 2. takeoff
        Seq("takeoff", Cond("needs_takeoff", needs_takeoff),
            Act("takeoff", act_takeoff)),

        # 3. mission
        Seq("mission", Cond("has_waypoint", has_waypoint),
            Act("goto_waypoint", act_goto_waypoint)),
        # 4. land
        Seq("land", Cond("mission_complete", mission_complete), Act("land", act_land)),

        # 5. fallback
        Act("hover", act_hover)
    ])
    return py_trees.trees.BehaviourTree(root)


def print_tree(tree: py_trees.trees.BehaviourTree) -> None:
    print(py_trees.display.unicode_tree(tree.root, show_status=True))