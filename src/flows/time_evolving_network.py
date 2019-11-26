import networkx as nx
import matplotlib.pyplot as plt

def parse_tuple_from_txt(tuple_str):
    interest = tuple_str.split("_")[0]
    interest_left = interest.split("(")[1].split(",")[0]
    interest_right = interest.split(")")[0].split(",")[1]
    return (int(interest_left),int(interest_right))


COLORS = ['b','g','r','c','m','y']
ORIENTATION_INBOUND = {0:"N",1:"E",2:"S",3:"W"}


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
				waiting_cost = 1, 
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


		self.topology_position = {}
		self.topology_swapping = {}

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
		self.list_cells = [parse_tuple_from_txt(x) for x in self.list_nodes]
		
		#connect the two layers
		self.graph.update(self.block)



		for i in range(depth-1):
			self.build_new_depth_network()

		self.compute_topology_network(graph_data)


	def connect_sources_and_sink(self, sources, sinks, directions = None):
		'''
		given a list of cells of sources and sinks,
		connect them to the graph in the followin manner: the source is attached at time t=0,
		while the sink is attached to all the time step > 1
		
		Parameters
		----------
		sources : list
			list of sources, they should be in the same format as self.list_cells
		sinks : list
			list of sources, they should be in the same format as self.list_cells
		
		Raises
		------
		ValueError
			if the length of the sources and the sinks differ
		ValueError
			if a source is not in self.list_cells
		ValueError
			if a sink is not in self.list_cells
		'''
		numbersConnection = 0
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

			#define node names
			source_name = "source_"+str(agent)
			sink_name = "sink_"+str(agent)

			#add the nodes to the graph
			self.graph.add_node(source_name,pos = [agent,-1])
			self.graph.add_node(sink_name,pos = [number_nodes +5 ,agent+0.2])

			#connect the source and sink nodes
			for node in self.graph.nodes:
				if node.startswith(str(source)) and "out" in node and  node.endswith("t0") :
					if directions is None:
						self.graph.add_edge(source_name,node, capacity = 1, weight = 0)
						numbersConnection += 1
					else:
						if ORIENTATION_INBOUND[directions[agent]] in node:
							self.graph.add_edge(source_name,node, capacity = 1, weight = 0)
							numbersConnection += 1

				if node.startswith(str(sink)) and 'in' in node and not node.endswith("t0"):
					self.graph.add_edge(node,sink_name, capacity = 1, weight = 0)
		if numbersConnection < len(sources):
			print("Error, not all sources were connected")		




	def build_base_layer(self,incoming_graph_data, 
						default_weight = 0, 
						default_capacity = 1e6, 
						waiting_cost = None,
						waiting_capacity = None):
		'''
		build the base layer for the time expanded graph, add a copy of the node to graph and 
		perform the connection between the time step 0 and the time step 1 
		
		Parameters
		----------
		incoming_graph_data : nx.Digraph
			original graph
		default_weight : int, optional
			default weight for the edges in the graph, by default 0
		default_capacity : int, optional
			default capacity for the edges in the graph, by default 1e6
		waiting_cost : int, optional
			default weight for the edges allowing one to stay in place trough time, by default None
		waiting_capacity : int, optional
			defautl capacity for the waiting edges, by default None
		'''

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

	def compute_topology_network(self,graph):
		'''
		get the topology of the network
		'''


		positionConstraints = graph.getPositionConstraints()
		swappingConstraints = graph.getSwappingConstraints()
		topology_position = {}
		topology_swapping = {}

		for i in range(self.last_time_step-1):
			topology_position[i] = {}
			topology_swapping[i] = {}
			for cell,c in positionConstraints.items():
				c_time = set()
				for edge in c:
					#transitions 
					c_time.add((edge[0]+"_t"+str(i),edge[1]+"_t"+str(i+1)))
					#stay in place
					if edge[0].split("_")[0] == edge[1].split("_")[0]:
						c_time.add((edge[0]+"_t"+str(i),edge[0]+"_t"+str(i+1)))
						c_time.add((edge[1]+"_t"+str(i),edge[1]+"_t"+str(i+1)))

				topology_position[i][cell] = c_time

			for cell,c in swappingConstraints.items():
				c_time = set()
				for edge in c:
					c_time.add((edge[0]+"_t"+str(i),edge[1]+"_t"+str(i+1)))
				topology_swapping[i][cell] = c_time
		
		
		self.topology_position = topology_position
		self.topology_swapping = topology_swapping


	def get_topology_network(self):
		'''
		returns a list of constraint (set of edges) and a dictionnary mapping each edge to 
		the constraints it belongs to 
		'''
		topology_liste = []
		for time,constraint in self.topology_position.items():
			for cell, pairs in constraint.items():
				topology_liste.append(set(pairs))
		for time,constraint in self.topology_swapping.items():
			for cell, pairs in constraint.items():
				topology_liste.append(set(pairs))

		findConstraints = {}
		for restriction in topology_liste:
			for edge in restriction:
				if edge not in findConstraints.keys():
					find_constraints[edge] = [restriction]
				else:
					findConstraints[edge].append(restriction)
				
		return topology_liste,findConstraints


	def build_new_depth_network(self):
		'''
		add one layer to the time expanded graph 
		'''
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
		'''
		rename the original nodes by giving them an appropriate time step
		'''
		layer_nodes = [self.update_time_stamp_names(x) for x in self.list_nodes]
		layer = nx.DiGraph()
		layer.add_nodes_from(layer_nodes)
		for i,node in enumerate(layer.nodes):
			layer.node[node]['pos'] = (i,int(node.split("_t")[-1]))
		return layer


	def update_time_stamp_names(self,name):
		'''
		update the time stamp of name 
		'''
		t = self.last_time_step
		name_updated = name + "_t" + str(t)
		return name_updated


	def show(self, details = False, paths = None):
		'''
		visualisation of the time expanded graph
		
		Parameters
		----------
		details : bool, optional
			show names, weights, capacity on the graph, by default False
		'''
		largeur = min(len(list(self.block.nodes))/2,20)
		longueur = min(int(3*(self.depth+1)),20)
		fig = plt.figure(figsize=(largeur,longueur))
		plt.rcParams['axes.facecolor'] = '#2e3037'
		pos=nx.get_node_attributes(self.graph,'pos')
		nx.draw(self.graph,pos, with_labels = details)
		weights = nx.get_edge_attributes(self.graph,'weight')
		capacities = nx.get_edge_attributes(self.graph,'capacity')
		labels = {}
		if details:
			for key in weights.keys():
				labels[key] = (weights[key],capacities[key])

		if paths is not None:
			for agent,path in paths.items():
				nx.draw_networkx_edges(self, pos,
						edgelist=path,
						width=10, alpha=1, edge_color=COLORS[int(agent)])
		_ = nx.draw_networkx_edge_labels(self.graph,pos,edge_labels=labels)
