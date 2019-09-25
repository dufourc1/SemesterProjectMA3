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

	The graph_high_level G = (V,E) with V the cells of the matrix in the env (RailEnv object), with E (undirected edges )
	representing the connection between two cells (a train can go from one to another)

	The graph_low_level G = (V,E) with G representing two nodes per cell in the matrix to represent the and E being 
	directed edges 
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
		'''
		create the graph representations from the env object
		'''

		#initialize the graphs
		graph_low_level = nx.DiGraph()
		graph_high_level = nx.DiGraph()

		#get the matrix representing the environment
		matrix_rail = np.array(self.rail.grid.tolist())

		self.__add_nodes(graph_high_level,graph_low_level,matrix_rail)

		self.__add_edges(graph_high_level,graph_low_level,matrix_rail)
		
		return  graph_high_level, graph_low_level


	def __add_edges(self,graph_high_level,graph_low_level,matrix_rail):
		'''
		add the edges to the graph
		'''

		for index,value in np.ndenumerate(matrix_rail):
			#self.__create_edges_one_cell(index,value,graph_high_level,'high')
			graph_low_level = self.__create_edges_one_cell(index,value,graph_low_level,'low')



	def __create_edges_one_cell(self,index,value,graph,level = 'high'):
		'''
		Given a cell transtions possibilities, create edges and connect the cell to its neighbour 
		with a convention to keep the "two way railway design" consistent in the case of th low
		level graph
		
		Parameters
		----------
		index : tuple
			coordinate of the cell in the matrix
		value : int
			value of the cell
		graph : networkx.Graph()
			graph with nodes corresponding to the matrix
		level : str, optional
			indicates which graph is dealt with, high or low level, by default 'high'
		'''

		#convertion
		binary_rep = cell_to_byte(value)
		name_node = tuple_to_str(index)


		if level == 'low':

			#get the possible transitions
			results = identify_crossing(binary_rep)
			for key,goals in results.items():
				#get the departing node based on from where the train is coming
				e1 = name_node + CONVENTION_FROM[key]
				for goal in goals:
					#get the goal node based on where the train is going
					e2 = tuple_to_str(get_node_direction(index,goal)) +CONVENTION_TOWARDS[goal]
					graph.add_edge(e1,e2)
			return graph
		elif level == 'high':
			raise NotImplementedError
		else:
			raise ValueError(f"only implementation for low and high level graphs, not {level}")

	
	def __add_nodes(self, graph_high_level,graph_low_level, matrix_rail):
		'''
		add nodes based on the matrix rail

		the names of the nodes are obtained in the following way: 
		(x,y) --> '000x000y' in the graph_high_level
		(x,y) --> {'000x000ya' ,''000x000yb'} in the graph_low_level
		'''

		#add the rails to the graph as nodes (rails are positive in the matrix)
		list_nodes = [tuple_to_str(index) for index, x in np.ndenumerate(matrix_rail) if x >0 ]
		graph_high_level.add_nodes_from(list_nodes)


		for elt in list_nodes:
			graph_low_level.add_node(elt + "a")
			graph_low_level.add_node(elt + "b")



	def show_graph(self,options = None):
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
					'node_size': 20,
					'width': 3,
					'arrowsize':10,
				}

		G = env.graph_low_level
		print(G.edges)
		pos = dict( (n, self.position(n)) for n in G.nodes() )
		nx.draw(G,pos = pos ,**options)
		plt.show()


	def position(self,node_str):
		ecart = 0.05
		index = str_to_tuple(node_str[:-1])
		y_coord = 0
		x_coord = index[0]
		if node_str[-1] == 'a':
			y_coord = index[1] + ecart
		else:
			y_coord = index[1] - ecart
		return (x_coord,y_coord)

if __name__ == '__main__':

	random.seed(1)
	np.random.seed(1)

	number_agents = 4

	size_side = 10
	env = EnvWrapperGraph(width=size_side,
              height=size_side,
              rail_generator=complex_rail_generator(nr_start_goal=10, nr_extra=1, min_dist=8, max_dist=99999, seed=0),
              schedule_generator=complex_schedule_generator(),
              number_of_agents=number_agents,
              obs_builder_object=GlobalObsForRailEnv())

	env.reset()


	
	env_renderer = RenderTool(env)
	env_renderer.render_env(show=True, show_predictions=False, show_observations=True)
	time.sleep(3)

	env.show_graph()

	
