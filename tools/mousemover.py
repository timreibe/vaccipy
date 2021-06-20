import math
import random
import time
from random import randint
from typing import Tuple

from selenium.common.exceptions import MoveTargetOutOfBoundsException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from tools.clog import CLogger


def move_mouse_by_offsets(x_coordinates: list, y_coordinates: list, driver) -> tuple:
    """Move mouse by offset to list of x and y coordinates

    Args:
        x_coordinates (list): x waypoints
        y_coordinates (list): y waypoints
        driver : Chromedriver

    Returns:
        tuple: Current mouse coordinates (mouse_x, mouse_y)
    """

    # Init current mouse position
    current_mouse_x = 0
    current_mouse_y = 0

    # Append mouse movement for each x,y coordinate
    for index, coordinate in enumerate(zip(x_coordinates, y_coordinates)):

        # Get current window size
        window_width = driver.get_window_size()["width"]
        window_height = driver.get_window_size()["height"]

        # If not first index calculate difference to last coordinate and update next offset
        if index:
            x_offset = coordinate[0] - x_coordinates[index - 1]
            y_offset = coordinate[1] - y_coordinates[index - 1]
        # First offset has no previous coordinate
        else:
            x_offset = coordinate[0]
            y_offset = coordinate[1]

        # Update predicted mouse position
        current_mouse_x = current_mouse_x + x_offset
        current_mouse_y = current_mouse_y + y_offset

        # Check wether predicted mouse position is out of bounds
        if not current_mouse_x >= window_width and not current_mouse_y >= window_height:
            # Append mouse movements
            try:
                ActionChains(driver).move_by_offset(x_offset, y_offset).perform()

            except MoveTargetOutOfBoundsException as e:
                pass

    time.sleep(randint(1, 5))

    return current_mouse_x, current_mouse_y


def generate_way_between_coordinates(source_x: int, source_y: int, target_x: int, target_y: int) -> tuple:
    """Generate random waypoints between two x,y coordinates without numpy

    Args:
        source_x (int): x coordinate of source
        source_y (int): y coordinate of source
        target_x (int): x coordinate of target
        target_y (int): y coordinate of target

    Returns:
        tuple: List of waypoints (x_coordinates, y_coordinates)
    """

    # Init and add source coordinates
    x_coordinates = [source_x]
    y_coordinates = [source_y]

    x_target_reached = False
    y_target_reached = False

    x_min_stepwidth = 3
    y_min_stepwidth = 3
    x_max_stepwidth = 50
    y_max_stepwidth = 50

    while not x_target_reached or not y_target_reached:

        # Create new random waypoints
        source_x = pick_next_step(source_x, target_x, x_max_stepwidth, x_min_stepwidth)
        source_y = pick_next_step(source_y, target_y, y_max_stepwidth, y_min_stepwidth)

        # If targets reached, stay at target
        if source_x == target_x:
            x_target_reached = True
        if source_y == target_y:
            y_target_reached = True

        # Wiggle a bit
        if not x_target_reached or not y_target_reached:
            if x_target_reached:
                source_x += random.randint(-x_min_stepwidth, x_min_stepwidth)
            if y_target_reached:
                source_y += random.randint(-y_min_stepwidth, y_min_stepwidth)

        # Append new waypoint coordinates
        x_coordinates.append(source_x)
        y_coordinates.append(source_y)

    # Don't hit exactly
    x_coordinates.append(source_x + random.randint(-x_min_stepwidth, x_min_stepwidth))
    y_coordinates.append(source_y + random.randint(-y_min_stepwidth, y_min_stepwidth))

    return x_coordinates, y_coordinates


def pick_next_step(source: int, target: int, max_stepwidth: int, min_stepwidth: int) -> int:
    """Find the next step on the way to the target

    Args:
        source (int): current point
        target (int): point to reach
        max_stepwidth (int): max stepwidth to the target
        min_stepwidth (int): min stepwidth to the target, can be overridden if nearer to the target

    Returns:
        int: next step to the target
    """
    dist_x = target - source
    step_x = 0
    if dist_x != 0:
        if abs(dist_x) <= max_stepwidth:
            step_x = dist_x
        else:
            step_x = math.copysign(randint(min_stepwidth, max_stepwidth), dist_x)
    return source + step_x


def move_mouse_to_element(log: CLogger, current_positon: Tuple[int, int], element: WebElement, driver: WebDriver) -> tuple:
    """Move mouse from x,y coordinates to the coordinates of the element

    Args:
        current_positon (tuple[int, int]): start position
        element (WebElement): target element
        driver (WebDriver): Chromedriver
    
    Returns:
        tuple: Current mouse coordinates (mouse_x, mouse_y)
    """
    return move_mouse_to_coordinates(log, current_positon[0], current_positon[1], element.location['x'], element.location['y'], driver)


def move_mouse_to_coordinates(log: CLogger, start_x: int, start_y: int, target_x: int, target_y: int, driver: WebDriver) -> tuple:
    """Move mouse from x,y coordinates to x,y coordinates

    Args:
        start_x (int): x coordinate of start position
        start_y (int): y coordinate of start position
        target_x (int): x coordinate of target position
        target_y (int): y x coordinate of target position
        driver : Chromedriver

    Returns:
        tuple: Current mouse coordinates (mouse_x, mouse_y)
    """

    # Generate waypoints
    coordinates_to_element = generate_way_between_coordinates(start_x, start_y, target_x, target_y)
    log.info(f"Simulation der Mausbewegungen gestartet. Von: ({start_x}, {start_y}) nach ({target_x}, {target_y})")
    # Execute movements and return coordinates
    return move_mouse_by_offsets(coordinates_to_element[0], coordinates_to_element[1], driver)
