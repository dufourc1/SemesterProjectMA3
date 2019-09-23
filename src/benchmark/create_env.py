import numpy as np
import networkx as nx
import random
import time

from utils import *

from flatland.envs.observations import *
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_generators import complex_rail_generator
from flatland.envs.schedule_generators import complex_schedule_generator
from flatland.utils.rendertools import RenderTool


import matplotlib.pyplot as plt
import json

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

		self.graph_high_level, self.graph_low_level = self.create_graph_from_env(self.obs_builder)



	def create_graph_from_env(self,observation_builder):

		#initialize the graphs
		graph_low_level = nx.DiGraph()
		graph_high_level = nx.DiGraph()

		#get the matrix representing the environment
		matrix_rail = np.array(self.rail.grid.tolist())

		self.__add_nodes(graph_high_level,graph_low_level,matrix_rail)

		self.__add_edges(graph_high_level,graph_low_level,matrix_rail)
		
		return  graph_high_level, graph_low_level


	def __add_edges(self,graph_high_level,graph_low_level,matrix_rail):

		for index,value in np.ndenumerate(matrix_rail):
			#self.__create_edges_one_cell(index,value,graph_high_level,'high')
			graph_low_level = self.__create_edges_one_cell(index,value,graph_low_level,'low')



	def __create_edges_one_cell(self,index,value,graph,level = 'high'):
		binary_rep = cell_to_byte(value)
		name_node = tuple_to_str(index)
		if level == 'low':
			results = identify_crossing(binary_rep)
			for key,goals in results.items():
				e1 = name_node + CONVENTION_FROM[key]
				for goal in goals:
					e2 = name_node +CONVENTION_TOWARDS[goal]
					graph.add_edge(e1,e2)
			return graph
		elif level == 'high':
			raise NotImplementedError
		else:
			raise ValueError(f"only implementation for low and high level graphs, not {level}")

	
	def __add_nodes(self, graph_high_level,graph_low_level, matrix_rail):

		#add the rails to the graph as nodes (rails are positive in the matrix)
		list_nodes = [tuple_to_str(index) for index, x in np.ndenumerate(matrix_rail) if x >0 ]
		graph_high_level.add_nodes_from(list_nodes)


		for elt in list_nodes:
			graph_low_level.add_node(elt + "a")
			graph_low_level.add_node(elt + "b")



	def show_graph(self,mode = 'spectral', options = None, node_names = False):
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
			nx.draw_spectral(env.graph_low_level,with_labels=node_names, **options)
			plt.show()
		elif mode == 'classic':
			nx.draw(env.graph_low_level,with_labels=node_names, **options)
			plt.show()
		else:
			raise ValueError(f'this mode of projection ({mode}) is not implemented yet')


if __name__ == '__main__':

	random.seed(1)
	np.random.seed(1)

	number_agents = 4


	env = EnvWrapperGraph(width=7,
              height=7,
              rail_generator=complex_rail_generator(nr_start_goal=10, nr_extra=1, min_dist=8, max_dist=99999, seed=0),
              schedule_generator=complex_schedule_generator(),
              number_of_agents=number_agents,
              obs_builder_object=GlobalObsForRailEnv())

	env.reset()


	
	env_renderer = RenderTool(env)
	env_renderer.render_env(show=True, show_predictions=False, show_observations=True)
	time.sleep(0.3)

	env.show_graph(mode = 'classic', node_names=False)
	G = env.graph_low_level
	print(G.edges)
	pos = dict( (n, str_to_tuple(n[:-1])) for n in G.nodes() )
	nx.draw(G,pos = pos)
	plt.show()