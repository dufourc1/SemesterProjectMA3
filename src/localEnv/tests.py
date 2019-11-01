import numpy as np

from flatland.envs.observations import TreeObsForRailEnv, GlobalObsForRailEnv
from flatland.envs.predictions import ShortestPathPredictorForRailEnv
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_generators import sparse_rail_generator
from flatland.envs.schedule_generators import sparse_schedule_generator
from flatland.utils.rendertools import RenderTool, AgentRenderVariant
from visualization.graphic import draw_square

np.random.seed(1)

# Use the new sparse_rail_generator to generate feasible network configurations with corresponding tasks
# Training on simple small tasks is the best way to get familiar with the environment

# Use a the malfunction generator to break agents from time to time
stochastic_data = {'prop_malfunction': 0.3,  # Percentage of defective agents
                   'malfunction_rate': 30,  # Rate of malfunction occurence
                   'min_duration': 3,  # Minimal duration of malfunction
                   'max_duration': 20  # Max duration of malfunction
                   }

# Custom observation builder
TreeObservation = TreeObsForRailEnv(max_depth=2, predictor=ShortestPathPredictorForRailEnv())

# Different agent types (trains) with different speeds.
speed_ration_map = {1.: 0.25,  # Fast passenger train
                    1. / 2.: 0.25,  # Fast freight train
                    1. / 3.: 0.25,  # Slow commuter train
                    1. / 4.: 0.25}  # Slow freight train

env = RailEnv(width=50,
              height=50,
              rail_generator=sparse_rail_generator(max_num_cities=4,
                                                   # Number of cities in map (where train stations are)
                                                   seed=14,  # Random seed
                                                   grid_mode=False,
                                                   max_rails_between_cities=2,
                                                   max_rails_in_city=8,
                                                   ),
              schedule_generator=sparse_schedule_generator(speed_ration_map),
              number_of_agents=3,
              stochastic_data=stochastic_data,  # Malfunction data generator
              obs_builder_object=GlobalObsForRailEnv(),
              remove_agents_at_target=True
              )

# RailEnv.DEPOT_POSITION = lambda agent, agent_handle : (agent_handle % env.height,0)
env.reset()

env_renderer = RenderTool(env,
                          agent_render_variant=AgentRenderVariant.AGENT_SHOWS_OPTIONS_AND_BOX,
                          show_debug=True,
                          screen_height=1100,
                          screen_width=1800)
env_renderer.reset()

env_renderer.render_env(show=True, show_observations=False, show_predictions=False)

