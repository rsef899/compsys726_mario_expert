"""
This the primary class for the Mario Expert agent. It contains the logic for the Mario Expert agent to play the game and choose actions.

Your goal is to implement the functions and methods required to enable choose_action to select the best action for the agent to take.

Original Mario Manual: https://www.thegameisafootarcade.com/wp-content/uploads/2017/04/Super-Mario-Land-Game-Manual.pdf
"""

import json
import logging
import random

import cv2
import numpy as np
from mario_environment import MarioEnvironment
from pyboy.utils import WindowEvent


# Constants
DOWN_ARROW = 0
LEFT_ARROW = 1
RIGHT_ARROW = 2
UP_ARROW = 3
BUTTON_A = 4
BUTTON_B = 5

# Object Mappings
MARIO = 1
PIPE = 14
UNCLAIMED_COIN = 13




class MarioController(MarioEnvironment):
    """
    The MarioController class represents a controller for the Mario game environment.

    You can build upon this class all you want to implement your Mario Expert agent.

    Args:
        act_freq (int): The frequency at which actions are performed. Defaults to 10.
        emulation_speed (int): The speed of the game emulation. Defaults to 0.
        headless (bool): Whether to run the game in headless mode. Defaults to False.
    """

    def __init__(
        self,
        act_freq: int = 6,
        emulation_speed: int = 1,
        headless: bool = False,
    ) -> None:
        super().__init__(
            act_freq=act_freq,
            emulation_speed=emulation_speed,
            headless=headless,
        )

        self.act_freq = act_freq

        # Example of valid actions based purely on the buttons you can press
        valid_actions: list[WindowEvent] = [
            WindowEvent.PRESS_ARROW_DOWN,
            WindowEvent.PRESS_ARROW_LEFT,
            WindowEvent.PRESS_ARROW_RIGHT,
            WindowEvent.PRESS_ARROW_UP,
            WindowEvent.PRESS_BUTTON_A,
            WindowEvent.PRESS_BUTTON_B,
        ]

        release_button: list[WindowEvent] = [
            WindowEvent.RELEASE_ARROW_DOWN,
            WindowEvent.RELEASE_ARROW_LEFT,
            WindowEvent.RELEASE_ARROW_RIGHT,
            WindowEvent.RELEASE_ARROW_UP,
            WindowEvent.RELEASE_BUTTON_A,
            WindowEvent.RELEASE_BUTTON_B,
        ]

        self.valid_actions = valid_actions
        self.release_button = release_button

    def run_action(self, action: int, duration: int) -> None:
        """
        This is a very basic example of how this function could be implemented

        As part of this assignment your job is to modify this function to better suit your needs

        You can change the action type to whatever you want or need just remember the base control of the game is pushing buttons
        """

        # Simply toggles the buttons being on or off for a duration of act_freq
        print(action)
        self.pyboy.send_input(self.valid_actions[action])
        for _ in range(duration):
            self.pyboy.tick()

        self.pyboy.send_input(self.release_button[action])
        


class MarioExpert:
    """
    The MarioExpert class represents an expert agent for playing the Mario game.

    Edit this class to implement the logic for the Mario Expert agent to play the game.

    Do NOT edit the input parameters for the __init__ method.

    Args:
        results_path (str): The path to save the results and video of the gameplay.
        headless (bool, optional): Whether to run the game in headless mode. Defaults to False.
    """

    # States

    NORMAL_MODE = 1
    ENEMY_MODE = 2
    COIN_MODE = 3

    # PowerUp state
    NORMAL_POWER = 1
    GIANT_POWER = 2
    SHOOTER_POWER = 3
    INVINCIBLE_MODE = 4

    # Memory Addresses
    MARIO_TOUCHING_GROUND = 0xC20A
    MARIO_SPEED = 0xC20C

    def __init__(self, results_path: str, headless=False):
        self.results_path = results_path

        self.environment = MarioController(headless=headless)

        self.video = None

        self.current_state = self.NORMAL_MODE
        self.powerup_state = self.NORMAL_POWER

    def mario_x_location(self):
        return self.environment._read_m(0xC202)

    def enemy_x_location(self):
        return self.environment._read_m(0xD103)
    
    def find_position(self, grid, value):
        """
        Find the position of the specified value in the grid.
        Returns the first occurrence of the value.
        """
        result = np.where(grid == value)
        if result[0].size > 0 and result[1].size > 0:
            return result[0][0], result[1][0]
        else:
            return None

    def mario_movement_to_loot(self, grid, consumable):
        # Convert the grid to a numpy array
        grid_np = np.array(grid)
        
        # Find positions of Mario (1) and loot (13)
        mario_position = self.find_position(grid_np, 1)
        loot_position = self.find_position(grid_np, consumable)
        
        direction_to_loot = DOWN_ARROW

        if mario_position is None:
            direction_to_loot = RIGHT_ARROW
        if loot_position is None:
            return DOWN_ARROW
        
        mario_row, mario_col = mario_position
        loot_row, loot_col = loot_position
        
        if (loot_col == mario_col or loot_col == mario_col + 1) and self.environment._read_m(self.MARIO_TOUCHING_GROUND) and self.environment._read_m(self.MARIO_SPEED) == 0:
            direction_to_loot = BUTTON_A
        elif (loot_col == mario_col or loot_col == mario_col + 1) and ~self.environment._read_m(self.MARIO_TOUCHING_GROUND) or ~self.environment._read_m(self.MARIO_SPEED) == 0:
            direction_to_loot = DOWN_ARROW
        elif mario_col < loot_col:
            direction_to_loot = RIGHT_ARROW
        elif mario_col > loot_col:
            direction_to_loot = LEFT_ARROW
        elif mario_row < loot_row and self.environment._read_m(self.MARIO_TOUCHING_GROUND) and self.environment._read_m(self.MARIO_SPEED) == 0:
            direction_to_loot = BUTTON_A
        else:
            direction_to_loot = DOWN_ARROW

        print(f"loot is {consumable} = mCOl=  {str(mario_col)} lCOL= { str(loot_col)} direction to loot = {str(direction_to_loot)}")
        return direction_to_loot


    def game_fsm(self):
        game_area = self.environment.game_area()
        print(game_area)

        mario_grid_position = self.find_position(game_area, 1)
        mario_row, mario_col = mario_grid_position

        match self.current_state:
            case self.NORMAL_MODE:
                if (game_area[mario_row][mario_col+3] != 0):
                    return (BUTTON_A, 10)
                else:
                    return RIGHT_ARROW
            case self.ENEMY_MODE:
                if ((self.mario_x_location() - self.enemy_x_location()) < 15 and self.environment._read_m(self.MARIO_TOUCHING_GROUND)):
                        return BUTTON_A
                elif ((self.mario_x_location() - self.enemy_x_location()) < 5) and self.environment._read_m(self.MARIO_TOUCHING_GROUND) and self.environment._read_m(self.MARIO_SPEED) == 0:
                    return BUTTON_A
                else:
                    return DOWN_ARROW
            case self.COIN_MODE:
                if np.any((np.isin(game_area, [6]))):
                    return self.mario_movement_to_loot(game_area, 6) 
                else:
                    return self.mario_movement_to_loot(game_area, 13)               
            
    def next_state(self):
        game_area = self.environment.game_area()
        print(game_area)

        mario_grid_position = self.find_position(game_area, 1)
        mario_row, mario_col = mario_grid_position

        print(f"The enemy is {self.environment._read_m(0xD100)}")
        print(f"MARIO PYGRIF x: {mario_col} y: {mario_row}, 2 infront = {game_area[mario_row][mario_col+2]}")
        match self.current_state:
            case self.NORMAL_MODE:
                if np.any(~(np.isin(game_area, [0, 1, 10, 13, 14, 6]))):
                    self.current_state = self.ENEMY_MODE
                elif np.any((np.isin(game_area, [13,6]))):
                    self.current_state = self.COIN_MODE
                elif np.any((np.isin(game_area, [0, 1, 10, 13, 14]))):
                    self.current_state = self.NORMAL_MODE
            case self.COIN_MODE:
                if (game_area[mario_row][mario_col+3] != 0):
                    self.current_state = self.NORMAL_MODE
                elif np.any(~(np.isin(game_area, [0, 1, 10, 13, 14, 6]))):
                    self.current_state = self.ENEMY_MODE
                elif np.any((np.isin(game_area, [13,6]))):
                    self.current_state = self.COIN_MODE
                elif np.any((np.isin(game_area, [0, 1, 10, 13, 14, 6]))):
                    self.current_state = self.NORMAL_MODE
            case self.ENEMY_MODE:
                if (game_area[mario_row][mario_col+3] != 0):
                    self.current_state = self.NORMAL_MODE
                elif np.any(~(np.isin(game_area, [0, 1, 10, 13, 14, 6]))):
                    self.current_state = self.ENEMY_MODE
                elif np.any((np.isin(game_area, [13,6]))):
                    self.current_state = self.COIN_MODE
                elif np.any((np.isin(game_area, [0, 1, 10, 13, 14]))):
                    self.current_state = self.NORMAL_MODE
                


    def choose_action(self):
        state = self.environment.game_state()
        frame = self.environment.grab_frame()
        game_area = self.environment.game_area()

        print(f"CURRENT STATE: {self.current_state}")

        # Implement your code here to choose the best action
        # time.sleep(0.1)
        

        return self.game_fsm()


    def step(self):
        """
        Modify this function as required to implement the Mario Expert agent's logic.

        This is just a very basic example
        """

        # Choose an action - button press or other...
        action_and_duration = self.choose_action()
        
        # Unpack action and duration with a default value for duration
        if isinstance(action_and_duration, tuple):
            action, duration = action_and_duration
        else:
            action = action_and_duration
            duration = self.environment.act_freq  # Default duration value, change as needed

        # Run the action on the environment
        self.environment.run_action(action, duration)

        self.next_state()


    def play(self):
        """
        Do NOT edit this method.
        """
        self.environment.reset()

        frame = self.environment.grab_frame()
        height, width, _ = frame.shape

        self.start_video(f"{self.results_path}/mario_expert.mp4", width, height)

        while not self.environment.get_game_over():
            frame = self.environment.grab_frame()
            self.video.write(frame)

            self.step()

        final_stats = self.environment.game_state()
        logging.info(f"Final Stats: {final_stats}")

        with open(f"{self.results_path}/results.json", "w", encoding="utf-8") as file:
            json.dump(final_stats, file)

        self.stop_video()

    def start_video(self, video_name, width, height, fps=30):
        """
        Do NOT edit this method.
        """
        self.video = cv2.VideoWriter(
            video_name, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
        )

    def stop_video(self) -> None:
        """
        Do NOT edit this method.
        """
        self.video.release()
