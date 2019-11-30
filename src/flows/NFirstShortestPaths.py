#class using network x to find the n first shortest path between two nodes in a graph
import networkx as nx
from copy import deepcopy

class PathFinder:

	def __init__(self,graph):
		#do a deep copy of the graph so we son't modify it 
		self.graph = nx.DiGraph()
		self.graph.add_edges_from(deepcopy(graph.edges))

		#put a weight of one on all the edges in the graph
		nx.set_edge_attributes(self.graph,1,"weight")

	def reset_weights(self):
		nx.set_edge_attributes(self.graph,1,"weight")


	def findShortestPaths(self,source,target,n):
		
		paths = []
		for i in range(n):
			#find shortest path as a list of nodes
			path = nx.shortest_path(self.graph,source,target, weight = "weight", method= 'dijkstra')
			
			#translate the paths from list of nodes to list of edges
			path_pair_nodes = [path[i: i + 2] for i in range(len(path)-1)]
			path_edges = [ (pair[0],pair[1]) for pair in path_pair_nodes]

			#append the path to the solution 
			paths.append(path_edges)

			#update all the first edge on this path by adding 1 to the edge weight
			for e in path_edges:
				self.graph[e[0]][e[1]]["weight"] += 1

		return paths