import numpy as np
from flatland.envs.observations import TreeObsForRailEnv
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_generators import complex_rail_generator
from flatland.envs.schedule_generators import complex_schedule_generator
from flatland.utils.rendertools import RenderTool
from lookuptable import LookUpTable
from visualization.graphic import draw_square
from agent import Agent
from env import LocalEnv

#%%
number_agents = 2#np.random.randint(1,5)
width = 10#np.random.randint(3,20)
height = 15#np.random.randint(3,20)
n_start_goal = 5
seed = 4

speed_ration_map = {1.: 0.25,  # Fast passenger train
                    1. / 2.: 0.25,  # Fast freight train
                    1. / 3.: 0.25,  # Slow commuter train
                    1. / 4.: 0.25}  # Slow freight train


env = RailEnv(width=width,
              height=height,
              rail_generator=complex_rail_generator(nr_start_goal=n_start_goal,
                                                    nr_extra=3,
                                                    min_dist=8,
                                                    max_dist=99999,
                                                    seed = seed),
              schedule_generator=complex_schedule_generator(speed_ratio_map=speed_ration_map),
              number_of_agents=number_agents,
              obs_builder_object=TreeObsForRailEnv(max_depth=5))
env.reset()


env_renderer = RenderTool(env,agent_render_variant=3)
env_renderer.reset()
env_renderer.render_env(show=True, show_predictions=False, show_observations=False)
env.step(dict(zip(range(number_agents),[2]*number_agents)))
#%%
#table = LookUpTable(env.rail.grid, make_table=True) 
#dico = table.table
#ag = Agent(env.agents[0])

my_env = LocalEnv(env.rail.grid, env.agents)


