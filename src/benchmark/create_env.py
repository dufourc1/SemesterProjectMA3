import numpy as np
import networkx as nx
import random
import time

from flatland.envs.observations import *
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_generators import complex_rail_generator
from flatland.envs.schedule_generators import complex_schedule_generator
from flatland.utils.rendertools import RenderTool



class EnvWrapperGraph(RailEnv):
	'''
	class wrapping the normal flatland env and adding on top of that a representation of the netwrok in networkx
	'''

	def __init__(self,
				width,
				height,
				rail_generator,
				schedule_generator,
				number_of_agents,
				obs_builder_object):
		super().__init__(width,height,rail_generator, 
						schedule_generator,number_of_agents,
						obs_builder_object)

		self.graph = self.create_graph_from_env(self.obs_builder)



	def create_graph_from_env(self,observation_builder):
		graph = nx.Graph()
		graph.add_node((1,2))
		return  graph


	def show_graph(self,mode = 'spectral', options = None):
		'''
		visualization of the graph
		'''
		try:
			import matplotlib.pyplot as plt
		except:
			raise ImportError("matplotlib.pyplot was not loaded")

		if options is None:
			options = {
					'node_color': 'steelblue',
					'node_size': 100,
					'width': 3,
				}
		if mode == 'spectral':
			nx.draw_spectral(env.graph, **options)
			plt.show()
		else:
			raise ValueError(f'this mode of projection ({mode}) is not implemented yet')


if __name__ == '__main__':

	random.seed(1)
	np.random.seed(1)

	number_agents = 2


	env = EnvWrapperGraph(width=7,
              height=7,
              rail_generator=complex_rail_generator(nr_start_goal=10, nr_extra=1, min_dist=8, max_dist=99999, seed=0),
              schedule_generator=complex_schedule_generator(),
              number_of_agents=number_agents,
              obs_builder_object=GlobalObsForRailEnv())

	env.reset()
	matrix = np.array(env.rail.grid.tolist())

	print(matrix.shape)
	print(matrix)

	
	env_renderer = RenderTool(env)
	env_renderer.render_env(show=True, show_predictions=False, show_observations=True)
	time.sleep(20)