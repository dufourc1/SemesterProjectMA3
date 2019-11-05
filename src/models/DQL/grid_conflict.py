from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_generators import rail_from_grid_transition_map
from flatland.envs.schedule_generators import sparse_schedule_generator
from flatland.utils.rendertools import RenderTool
import numpy as np

grid = np.array([[ 8192,     0,  8192,     0,     0],
        [   72, 20994,  2064,     0,     0],
        [    0, 32872,  4608,     0,     0],
        [    0, 32800,    128,   0,     0],
        [    0,   128,     0,     0,     0]])



env = RailEnv(width = 5,
              height = 5,
              rail_generator=rail_from_grid_transition_map(grid),
              number_of_agents=1)

env.reset()

env_renderer = RenderTool(env)
env_renderer.render_env(show=True, show_predictions=False, show_observations=False)
