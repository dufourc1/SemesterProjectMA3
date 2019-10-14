#%%


import random
import numpy as np
from flatland.envs.observations import TreeObsForRailEnv
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_generators import complex_rail_generator
from flatland.envs.schedule_generators import complex_schedule_generator
from flatland.utils.rendertools import RenderTool
from visualization.graphic import graphic_coordinate,draw_path,draw_multiple_paths
from navigation.navigation_path import actions_for_path,walk_path,walk_many_paths

#%%

random.seed(1)
np.random.seed(1)

number_agents = 2
features_per_node = 9

env = RailEnv(width=7,
              height=7,
              rail_generator=complex_rail_generator(nr_start_goal=10, nr_extra=1, min_dist=8, max_dist=99999, seed=1),
              schedule_generator=complex_schedule_generator(),
              number_of_agents=number_agents,
              obs_builder_object=TreeObsForRailEnv(max_depth=2))
env.reset()

env_renderer = RenderTool(env)
env_renderer.render_env(show=True, show_predictions=False, show_observations=False)

#%%

path_0 = [(0,1),(0,2),(1,2),(1,3),(2,3),(2,4),(2,5),(3,5),(4,5),(5,5)]
path_1 = [(4,1),(3,1),(3,2),(3,3),(3,3),(2,3),(1,3),(1,4),(1,5),(1,6),(1,7)]
paths = [path_0, path_1]

walk_many_paths(env,env_renderer,paths,draw=True)
#draw_path(env_renderer,path)
#draw_multiple_paths(env_renderer,paths)
#obs = env.obs_builder.get(0)
#rail_data, distance_data, agent_data = split_tree(tree=np.array(obs),
#                                                          num_features_per_node=features_per_node,
#                                                          current_depth=0)
#actions = actions_for_path(path,3)
#walk_path(env,env_renderer,path_0,0)


#%%
