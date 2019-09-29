import numpy as np
import networkx as nx
import random
import time

from utils import *


from flatland.envs.observations import *
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_generators import complex_rail_generator,rail_from_manual_specifications_generator,random_rail_generator, RailGenerator
from flatland.envs.schedule_generators import complex_schedule_generator, random_schedule_generator, ScheduleGenerator
from flatland.utils.rendertools import RenderTool
from itertools import count

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
                 rail_generator: RailGenerator = random_rail_generator(),
                 schedule_generator: ScheduleGenerator = random_schedule_generator(),
                 number_of_agents=1,
                 obs_builder_object: ObservationBuilder = TreeObsForRailEnv(max_depth=2),
                 max_episode_steps=None,
                 stochastic_data=None
                 ):
		super().__init__(width,height,rail_generator, 
						schedule_generator,number_of_agents,
						obs_builder_object)

		self.graph_high_level, self.graph_low_level = self.create_graph_from_env(self.obs_builder)


	def recompute_graph(self):
		self.graph_high_level, self.graph_low_level = self.create_graph_from_env(self.obs_builder)

	def create_graph_from_env(self,observation_builder):
		'''
		create the graph representations from the env object
		'''

		#initialize the graphs
		graph_low_level = nx.DiGraph()
		graph_high_level = nx.Graph()

		#get the matrix representing the environment
		matrix_rail = np.array(self.rail.grid.tolist())

		self.__add_nodes(graph_high_level,graph_low_level,matrix_rail)

		self.__add_edges(graph_high_level,graph_low_level,matrix_rail)

		for node,_ in np.ndenumerate(matrix_rail):
			if tuple_to_str(node) in graph_high_level.nodes:
				check, error = is_wrong_connections(node, graph_low_level, matrix_rail)
				if check:
					print(f'node {node} has a bad connection: {error}')

		#correct the low_level_graph
		self.__correct_graph(matrix_rail,graph_low_level)


		for node,_ in np.ndenumerate(matrix_rail):
			if tuple_to_str(node) in graph_high_level.nodes:
				check, error = is_wrong_connections(node, graph_low_level, matrix_rail)
				if check:
					print(f'node {node} has a bad connection: {error}')


		return  graph_high_level, graph_low_level


	def __add_edges(self,graph_high_level,graph_low_level,matrix_rail):
		'''
		add the edges to the graph
		'''

		for index,value in np.ndenumerate(matrix_rail):
			self.__create_edges_one_cell(index,value,graph_high_level,'high')
			self.__create_edges_one_cell(index,value,graph_low_level,'low',matrix_rail)



	def __create_edges_one_cell(self,index,value,graph,level = 'high', matrix_rail = None):
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


		#conversion
		name_node = tuple_to_str(index)

		if level == 'low':
			# #get the possible transitions
			# results = identify_crossing(value)
			# for key,goals in results.items():
			# 	#get the departing node based on from where the train is coming
			# 	e1 = name_node + CONVENTION[key]
			# 	for goal in goals:
			# 		#get the goal node based on where the train is going
			# 		e2 = tuple_to_str(get_node_direction(index,goal)) +CONVENTION[goal]
			# 		if e1 in graph.nodes and e2 in graph.nodes:	
			# 			print(f'added {e1,e2} since {index}, from {key} to {goal}')
			# 			graph.add_edge(e1,e2)
			# 		else:
			# 			print(f'warning on edge {e1}-->{e2}')
			list_edges = transitions_to_edges(index,matrix_rail)
			graph.add_edges_from(list_edges)

		elif level == 'high':
			results = identify_crossing(value)
			for start,end in results.items():
				for goal in end:
					e2 = tuple_to_str(get_node_direction(index,goal))
					if name_node in graph.nodes and e2 in graph.nodes:
						graph.add_edge(name_node,e2)
					else:
						print(f'warning on edges ({name_node},{e2})')
		else:
			raise ValueError(f"only implementation for low and high level graphs, not {level}")

	
	def __correct_graph(self,matrix, graph_low_level):
		correct_double_edges_if_needed(graph_low_level,matrix)
		for index,value in np.ndenumerate(matrix):
			swap_if_needed(index,graph_low_level,matrix)
			

		


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
			graph_low_level.add_node(elt + "a", group = 'a')
			graph_low_level.add_node(elt + "b", group = 'b')

	def show_graph(self,high_level = True,options = None, figsize = (10,10)):
		'''
		visualization of the graph
		'''
		try:
			import matplotlib.pyplot as plt
		except:
			raise ImportError("matplotlib.pyplot was not loaded")

		if options is None:
			
			options = {
					'node_size': 50,
					'width': 3,
					'arrowsize':10,
				}


		

		if high_level:
			G = self.graph_high_level
			node_color = 'steel_blue'
			pos = dict( (n, self.position(n,high_level)) for n in G.nodes() )
			nx.draw(G ,pos,with_labels = False,  **options)
		else:
			G = self.graph_low_level
			pos = dict( (n, self.position(n,high_level)) for n in G.nodes() )
			groups = set(nx.get_node_attributes(G,'group').values())
			mapping = dict(zip(sorted(groups),count()))
			nodes = G.nodes()
			plt.figure(figsize=figsize)
			colors = [mapping[G.node[n]['group']] for n in nodes]
			ec = nx.draw_networkx_edges(G, pos, alpha=0.2)
			nc = nx.draw_networkx_nodes(G, pos, nodelist=nodes, node_color=colors, 
                            with_labels=False, node_size=100, cmap=plt.cm.jet)
		

		plt.show()

	def position(self,node_str, high_level= True):
		ecart = 0.1
		if high_level:
			index = str_to_tuple(node_str)
		else:
			index = str_to_tuple(node_str[:-1])

		if high_level:
			return (index[1],-index[0])
		
		else:
			y_coord = index[1]
			x_coord = index[0]
			if node_str[-1] == 'a':
				y_coord = index[1] + ecart
				x_coord = index[0] + ecart
			else:
				y_coord = index[1] - ecart
				x_coord = index[0] - ecart

			return (y_coord,-x_coord)


		



if __name__ == '__main__':

	random.seed(1)
	np.random.seed(1)

	number_agents = 4

	size_side = 5
	env = EnvWrapperGraph(width=size_side,
              height=size_side,
              rail_generator=complex_rail_generator(nr_start_goal=10, nr_extra=1, min_dist=8, max_dist=99999, seed=0),
              schedule_generator=complex_schedule_generator(),
              number_of_agents=number_agents,
              obs_builder_object=GlobalObsForRailEnv())


	env.reset()


	
	# env_renderer = RenderTool(env)
	# env_renderer.render_env(show=True, show_predictions=False, show_observations=True)
	# time.sleep(3)

	env.show_graph(high_level=False)






