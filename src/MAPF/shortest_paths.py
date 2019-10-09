'''
implementation of shortest paths methods
'''

import networkx as nx

class Dijkstra:

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.name = "Dijkstra"

	def find_paths(self,starting_points,goals,graph):
		'''
		given two arrays of starting points and goals points named as the real nodes names in the graph,
		return a list of shortest paths in the same order

		the paths returned are defined as a list of nodes

		if not path is available return an empty list
		
		Parameters
		----------
		starting_points : list
			[s_1,s_2,...,s_n]
		goals : list
			[g_1,g_2,...,g_n]
		
		Returns
		--------
		paths: list of list
			 [
				 [s_1,v_2,...,v_k,g_1],
				 ...
			 ]
		'''

		#sanity check for the input
		assert len(goals) == len(starting_points), f'length of starting points and goals points differ : {len(goals),len(starting_points)}'
		assert all(x in graph.nodes for x in starting_points), 'some starting points are not in the graph'
		assert all(x in graph.nodes for x in goals), 'some goals points are not in the graph'

		#algorithm
		paths = []
		for start,goal in zip(starting_points,goals):
			try:
				paths.append(nx.dijkstra_path(graph,start,goal))
			except(nx.NetworkXNoPath):
				paths.append([])

		return paths

