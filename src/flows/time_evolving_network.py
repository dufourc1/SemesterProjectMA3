import networkx as nx
import matplotlib.pyplot as plt


class TimeNetwork:

	'''
	Implementation of a time connected network

	Examples
	--------
	\\>> graph = nx.complete_graph(100)

	\\>> timeExpandedNetwork = TimeNetwork(graph)
		# get the actual time expanded graph
	\\>> graphTime = timeExpandedGraph.graph
	'''


	def __init__(self, 
				graph_data,
				depth = 1,
				default_weight = 0,
				default_capacity = 1, 
				waiting_cost = 0, 
				waiting_capacity = 1):
	

		if depth < 1:
			print(f'IllegalArgumentWarning depth {depth} should be greater than 1, setting it to 1')
			depth = 1


		#reduce the nodes space by dropping from the graph the isolated vertices
		incoming_graph_data = nx.DiGraph()
		incoming_graph_data.add_edges_from(graph_data.edges)
		incoming_graph_data.remove_nodes_from(list(nx.isolates(incoming_graph_data)))
		
		self.depth = depth
		self.graph = nx.DiGraph()


		self.default_capacity = default_capacity
		self.default_weight = default_weight
		#the building block of the time expanded graph: one time step expansion + one intermediate layer
		self.block = nx.DiGraph()
		self.last_time_step = 0

		#extract the nodes and build the first layer of the time expanded graph
		self.block, self.list_nodes = self.build_base_layer(incoming_graph_data = incoming_graph_data,
																	default_capacity = default_capacity,
																	default_weight = default_weight,
																	waiting_cost = waiting_cost,
																	waiting_capacity = waiting_capacity)

		#take the cell index for the flatland graph
		self.list_cells = [(int(x.split("_")[0][1]), int(x.split("_")[0][-2])) for x in self.list_nodes]
		
		#connect the two layers
		self.graph.update(self.block)



		for i in range(depth-1):
			self.build_new_depth_network()

		self.topology = self.get_topology_network()


	def connect_sources_and_sink(self, sources, sinks):

		if len(sources) != len(sinks):
			raise ValueError("number of sources and sinks is different ! ")
		for i,s in enumerate(sources):
			if s not in self.list_cells:
				raise ValueError(f'source for commodity {i}: {s} is not in the orginal graph')
		for i,s in enumerate(sinks):
			if s not in self.list_cells:
				raise ValueError(f'sink for commodity {i}: {s} is not in the orginal graph')
		
		number_nodes = len(list(self.block.nodes))/2
		for agent, (source,sink) in enumerate(zip(sources,sinks)):
			source_name = "source_agent_"+str(agent)
			sink_name = "sink_agent_"+str(agent)
			self.graph.add_node(source_name,pos = [agent,-1])
			self.graph.add_node(sink_name,pos = [number_nodes +5 ,agent+0.2])
			for node in self.graph.nodes:
				if node.startswith(str(source)) and 'out' in node and node.endswith("t0") :
					self.graph.add_edge(source_name,node, capacity = 1, weight = 0)
				if node.startswith(str(sink)) and 'in' in node:
					if not node.endswith("0"):
						self.graph.add_edge(node,sink_name, capacity = 1, weight = 0)
		
		self.topology = self.get_topology_network()




	def build_base_layer(self,incoming_graph_data, 
						default_weight = 0, 
						default_capacity = 1e6, 
						waiting_cost = None,
						waiting_capacity = None):

		#keeping track of the layer
		t = self.last_time_step
		list_nodes = []

		basis_layer = nx.DiGraph()



		#build the two layers of the node
		for i,node in enumerate(incoming_graph_data.nodes):

			#extract the type of the node: src (s1), sink (t1), or nothing
			try:
				type_node = incoming_graph_data.node[node]['type_node']
			except(KeyError):
				type_node = "transshipment"

			#keep track of the old name in the graph
			old_name = node
			list_nodes.append(str(old_name))

			#add the nodes for one time step
			name_time_t = str(node)+"_t" + str(t)
			name_time_t_1 = str(node)+"_t" + str(t+1)
			basis_layer.add_node(name_time_t,type_node = type_node,old_name = old_name, pos = (i,t))
			basis_layer.add_node(name_time_t_1,type_node = type_node,old_name = old_name, pos = (i,t+1))

			#add a waiting edge between them if needed
			if waiting_cost is not None:
				basis_layer.add_edges_from([(name_time_t,name_time_t_1)],weight = waiting_cost,capacity = waiting_capacity)


		for edge in incoming_graph_data.edges:

			#get the dictionnary with the relevant info from the original graph
			data_edge = incoming_graph_data[edge[0]][edge[1]]

			new_data_edge = {}
			if 'capacity' in data_edge.keys():
				new_data_edge['capacity'] = data_edge['capacity']
			else:
				new_data_edge['capacity'] = default_capacity
				
			if 'weight' in data_edge.keys():
				new_data_edge['weight'] = data_edge['weight']
			else:
				new_data_edge['weight'] = 1

			#get the updated endpoints for the graph
			basis_layer.add_edges_from([(str(edge[0])+"_t"+str(t),str(edge[1])+"_t"+str(t+1))],**new_data_edge)

		#update the number of layer existing
		self.last_time_step += 2
		return basis_layer, list_nodes

	def get_topology_network(self):
		'''
		get the topology of the network
		'''
		topology_dict = {}
		for cell in self.list_cells:
			topology_dict[cell] = {}
		for edge in self.graph.edges:
			for key,item in topology_dict.items():
				if edge[0].startswith(str(key)) and edge[1].startswith(str(key)):
					if abs(int(edge[0].split("_t")[-1]) - int(edge[1].split("_t")[-1]))==1:
						time = int(edge[0].split("_t")[-1])
						if time in topology_dict[key].keys():
							topology_dict[key][time].add(edge)
						else:
							topology_dict[key][time] = set()
							topology_dict[key][time].add(edge)
						break
		
		topology = []
		for _, item in topology_dict.items():
			for _,item2 in item.items():
				topology.append(item2)
		
		return topology

	def get_swapping_edges(self):
		'''
		

		Returns
		-------
		swapping_edges : list of set
			list of disjoint set, each set contains all the possible ways to go from cell1 to cell2 and vice-versa
		'''
		raise NotImplementedError





	def build_new_depth_network(self):

		#get the new block to add with the updated name wrt to time stamp
		layer_new = self.updated_name_block()
		self.graph.update(layer_new)

		for edge in self.block.edges:

			#get the dictionnary with the relevant info from the original graph
			data_edge = self.block[edge[0]][edge[1]]

			new_data_edge = {}
			if 'capacity' in data_edge.keys():
				new_data_edge['capacity'] = data_edge['capacity']
			else:
				new_data_edge['capacity'] = self.default_capacity
				
			if 'weight' in data_edge.keys():
				new_data_edge['weight'] = data_edge['weight']
			else:
				new_data_edge['weight'] = self.default_weight

			#get the updated endpoints for the graph
			old_name_node_from = edge[0].split("_t")[0]
			old_name_node_to = edge[1].split("_t")[0]

			new_name_node_from = old_name_node_from+"_t"+str(self.last_time_step-1)
			new_name_node_to = old_name_node_to +"_t"+str(self.last_time_step)

			self.graph.add_edges_from([(new_name_node_from,new_name_node_to)],**new_data_edge)

		self.last_time_step += 1
	


	def updated_name_block(self):
		layer_nodes = [self.update_time_stamp_names(x) for x in self.list_nodes]
		layer = nx.DiGraph()
		layer.add_nodes_from(layer_nodes)
		for i,node in enumerate(layer.nodes):
			layer.node[node]['pos'] = (i,int(node.split("_t")[-1]))
		return layer


	def update_time_stamp_names(self,name):
		t = self.last_time_step
		name_updated = name + "_t" + str(t)
		return name_updated


	def show(self, details = False):
		largeur = min(len(list(self.block.nodes))/2,20)
		longueur = min(int(3*(self.depth+1)),20)
		plt.figure(figsize=(largeur,longueur))
		pos=nx.get_node_attributes(self.graph,'pos')
		nx.draw(self.graph,pos, with_labels = details)
		weights = nx.get_edge_attributes(self.graph,'weight')
		capacities = nx.get_edge_attributes(self.graph,'capacity')
		labels = {}
		if details:
			for key in weights.keys():
				labels[key] = (weights[key],capacities[key])
		_ = nx.draw_networkx_edge_labels(self.graph,pos,edge_labels=labels)