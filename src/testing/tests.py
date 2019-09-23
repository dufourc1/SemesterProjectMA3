#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 23 00:04:53 2019

@author: red
"""

import random

import numpy as np

from flatland.envs.observations import TreeObsForRailEnv
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_generators import complex_rail_generator
from flatland.envs.schedule_generators import complex_schedule_generator
from flatland.utils.rendertools import RenderTool
from utils.observation_utils import normalize_observation, split_tree


random.seed(1)
np.random.seed(1)

number_agents = 2
features_per_node = 9

env = RailEnv(width=7,
              height=7,
              rail_generator=complex_rail_generator(nr_start_goal=10, nr_extra=1, min_dist=8, max_dist=99999, seed=0),
              schedule_generator=complex_schedule_generator(),
              number_of_agents=number_agents,
              obs_builder_object=TreeObsForRailEnv(max_depth=2))
env.reset()

env_renderer = RenderTool(env)
env_renderer.render_env(show=True, show_predictions=False, show_observations=True)

#%%

obs = env.obs_builder.get(0)
rail_data, distance_data, agent_data = split_tree(tree=np.array(obs),
                                                          num_features_per_node=features_per_node,
                                                          current_depth=0)
 
env.obs_builder.util_print_obs_subtree(tree=obs)
    """
    Splits the tree observation into different sub groups that need the same normalization.
    This is necessary because the tree observation includes two different distance:
    1. Distance from the agent --> This is measured in cells from current agent location
    2. Distance to targer --> This is measured as distance from cell to agent target
    3. Binary data --> Contains information about presence of object --> No normalization necessary
    Number 1. will depend on the depth and size of the tree search
    Number 2. will depend on the size of the map and thus the max distance on the map
    Number 3. Is independent of tree depth and map size and thus must be handled differently
    Therefore we split the tree into these two classes for better normalization.
    :param tree: Tree that needs to be split
    :param num_features_per_node: Features per node ATTENTION! this parameter is vital to correct splitting of the tree.
    :param current_depth: Keeping track of the current depth in the tree
    :return: Returns the three different groups of distance and binary values.
    """
  