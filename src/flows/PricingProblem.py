# class to solve the pricing problem for the multicommodity flow 
# column generation framework

import networkx as nx
from copy import deepcopy

class PricingSolver:

	def __init__(self,graph, constraints,findConstraints,numberOfCommodities):
		self.graph = nx.DiGraph()
		self.graph.add_edges_from([deepcopy(e) for e in graph.edges])
		self.__set_sources_sinks(numberOfCommodities)
		self.findConstraints = findConstraints


	def __set_sources_sinks(self,numberOfCommodities):
		self.sources = []
		self.targets = []
		for i in range(numberOfCommodities):
			self.sources.append("source_"+str(i))
			self.targets.append("sink_"+str(i))


	def get_columns_to_add(self,dualVariables, constraintsAcitvated):
		
		paths_to_add = []
		self.set_weights(dualVariables,constraintsAcitvated)

		for i,(s,t) in enumerate(zip(self.sources,self.targets)):
			#get the sigma dual variables from the array
			
			sigma = dualVariables[-len(self.sources)+i]

			improvable, path = self.check_if_improvable(s,t,sigma)
			if improvable:
				paths_to_add.append(path)

		return [[(path[i],path[i+1]) for i in range(len(path)-1)] for path in paths_to_add]


	def set_weights(self,dualVariables, constraintsActivated):
		'''
		Get the weights of the constraints (dual variable from the LP) and set them as attributes of the edges
		'''

		# see remark in the report on non activated constraints to get why 
		# default value is 0 (then the actual edge weight is 1)
		nx.set_edge_attributes(self.graph,1,"weight")
		for i,constraint in enumerate(constraintsActivated):
			for edge in constraint:
				self.graph[edge[0]][edge[1]]["weight"] += dualVariables[i]

		

	def check_if_improvable(self,s,t,sigma):
		'''
		check if the the minimum weighted path from s to t has weight 
		smaller than sigma and return the min weigthed path found	

		Parameters
		----------
		s : string \\
			source node, must be in the graph use for initialization of the Pricing solver\\
		t : string\\
			sink node, must be in the graph use for initialization of the Pricing solver\\
		sigma : double

		
		Returns
		-------
		Tuple (Boolean, List)\\
			return True if the min weighted path has weight smaller than sigma
			return the min weighted path between s and t
		'''

		#compute shortest weighted path
		min_weight_path = nx.shortest_path(self.graph,s,t,"weight")
		min_weight = self.compute_path_length(min_weight_path)

		if min_weight < sigma:
			return True,min_weight_path
		else:
			return False,min_weight_path


	def compute_path_length(self,path):
		total_length = 0
		for i in range(len(path)-1):
			source, target = path[i], path[i+1]
			edge = self.graph[source][target]
			total_length += edge['weight']

		return total_length
