#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 16 11:54:04 2019

@author: red
"""

import numpy as np
import time
import flatland
from flatland.envs.rail_generators import complex_rail_generator
from flatland.envs.schedule_generators import complex_schedule_generator
from flatland.envs.rail_env import RailEnv
from flatland.utils.rendertools import RenderTool
from flatland.envs.rail_generators import rail_from_manual_specifications_generator
from flatland.envs.rail_generators import random_rail_generator
from flatland.envs.observations import TreeObsForRailEnv
#%%
NUMBER_OF_AGENTS = 10
env = RailEnv(
            width=20,
            height=20,
            rail_generator=complex_rail_generator(
                                    nr_start_goal=10,
                                    nr_extra=1,
                                    min_dist=8,
                                    max_dist=99999,
                                    seed=0),
            schedule_generator=complex_schedule_generator(),
            number_of_agents=NUMBER_OF_AGENTS)

env_renderer = RenderTool(env)


for step in range(100):

    _action = my_controller()
    obs, all_rewards, done, _ = env.step(_action)
    print("Rewards: {}, [done={}]".format( all_rewards, done))
    env_renderer.render_env(show=True, frames=False, show_observations=False)
    time.sleep(0.3)

#%%

specs = [[(0, 0), (0, 0), (0, 0), (0, 0), (0, 0), (0, 0)],
         [(0, 0), (0, 0), (0, 0), (0, 0), (7, 0), (0, 0)],
         [(7, 270), (1, 90), (1, 90), (1, 90), (2, 90), (7, 90)],
         [(0, 0), (0, 0), (0, 0), (0, 0), (0, 0), (0, 0)]]


env = RailEnv(width=6,
              height=4,
              rail_generator=rail_from_manual_specifications_generator(specs),
              number_of_agents=1,
              obs_builder_object=TreeObsForRailEnv(max_depth=2))



env_renderer = RenderTool(env)

_action = {0:5}
obs, all_rewards, done, _ = env.step(_action)
print("Rewards: {}, [done={}]".format( all_rewards, done))
env_renderer.render_env(show=True, frames=False, show_observations=False)




#%%

# Relative weights of each cell type to be used by the random rail generators.
transition_probability = [1.0,  # empty cell - Case 0
                          1.0,  # Case 1 - straight
                          1.0,  # Case 2 - simple switch
                          0.3,  # Case 3 - diamond drossing
                          0.5,  # Case 4 - single slip
                          0.5,  # Case 5 - double slip
                          0.2,  # Case 6 - symmetrical
                          0.0,  # Case 7 - dead end
                          0.2,  # Case 8 - turn left
                          0.2,  # Case 9 - turn right
                          1.0]  # Case 10 - mirrored switch

# Example generate a random rail.
env = RailEnv(width=10,
              height=10,
              rail_generator=random_rail_generator(
                        cell_type_relative_proportion=transition_probability
                        ),
              number_of_agents=3,
              obs_builder_object=TreeObsForRailEnv(max_depth=2))

RenderTool(env).render_env(show=True)
              
#%%

              
