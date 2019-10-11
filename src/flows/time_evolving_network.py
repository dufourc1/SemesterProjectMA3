import networkx as nx
import matplotlib.pyplot as plt


class TimeNetwork:

	'''
	Time expanded network
	'''


	def __init__(self, 
				incoming_graph_data = None,
				depth = 1,
				default_weight = 0,
				default_capacity = 1e10, 
				waiting_cost = 0, 
				waiting_capacity = 1e6,
				intermediate_weight = 0,
				intermediate_capacity = 1):
		

		'''
		[summary]
		
		Parameters
		----------
		incoming_graph_data : nx.DiGraph
			[description]

		default_weight : float, optional
			[description], by default 0

		default_capacity : float, optional
			[description], by default 1e10
		'''

		#the time expanded graph
		self.graph = nx.DiGraph()

		#the building block of the time expanded graph: one time step expansion + one intermediate layer
		self.block = nx.DiGraph()
		self.last_time_step = 0


		#extract the nodes and build the first layer of the time expanded graph
		self.basis_layer, self.list_nodes = self.build_base_layer(incoming_graph_data = incoming_graph_data,
																	default_capacity = default_capacity,
																	default_weight = default_weight,
																	waiting_cost = waiting_cost,
																	waiting_capacity = waiting_capacity)

		#build the intermediate layer
		self.intermediate_layer = self.build_intermediate_layer(incoming_graph_data,
																intermediate_weight,
																intermediate_capacity)

		#connect the two layers
		self.block = self.connect_first_layers()
		self.graph.update(self.block)

		for i in range(depth):
			self.build_new_depth_network()



		# self.connect_sources_and_sink()

		


	def connect_sources_and_sink(self):

		raise NotImplementedError


	def build_base_layer(self,incoming_graph_data, 
						default_weight = 0, 
						default_capacity = 1e6, 
						waiting_cost = None,
						waiting_capacity = None):
		'''
		[summary]
		
		Parameters
		----------
		incoming_graph_data : nx.DiGraph, optional
			[description], by default None
			by default does not allow for self loop

		t : int, optional
			[description], by default 0

		default_weight : float, optional
			[description], by default 0

		default_capacity : float, optional
			[description], by default 1e6

		waiting_cost : [type], optional
			[description], by default None

		waiting_capacity : [type], optional
			[description], by default None


		Returns
		--------

		basis_layer: nx.DiGraph
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
				new_data_edge['weight'] = default_weight

			#get the updated endpoints for the graph
			basis_layer.add_edges_from([(str(edge[0])+"_t"+str(t),str(edge[1])+"_t"+str(t+1))],**new_data_edge)

		#update the number of layer existing
		self.last_time_step += 2
		return basis_layer, list_nodes

	def build_intermediate_layer(self,
								incoming_graph_data,
								intermediate_weight,
								intermediate_capacity):

		inter_layer = nx.DiGraph()
		for i,node in enumerate(self.list_nodes):
			inter_layer.add_node(node+"_t"+str(self.last_time_step),pos = (i,self.last_time_step))
		self.last_time_step += 1

		return inter_layer

	def connect_first_layers(self):
		'''
		[summary]
		
		Returns
		-------
		[type]
			[description]
		'''

		graph_inter = nx.DiGraph()
		graph_inter.update(self.basis_layer)
		graph_inter.update(self.intermediate_layer)
		
		#get the upper layer of the basislayer
		time_stamps = set([int(x.split("_t")[-1]) for x in self.basis_layer.nodes])

		nodes_to_connect_basis_layer = [node for node in self.basis_layer.nodes if int(node.split("_t")[-1])==max(time_stamps)]

		for node in nodes_to_connect_basis_layer:

			#get the true name of the node and the corresponding time step 
			name_node,t = node.split("_t")
			t = int(t)

			graph_inter.add_edge(node,name_node + "_t"+str(t+1), weight = 0, capacity = 1)


		return graph_inter


	def build_new_depth_network(self):

		#get the new block to add with the updated name wrt to time stamp
		layer_new = self.updated_name_block()

		nodes_to_connect_basis_layer = [node for node in self.graph.nodes if int(node.split("_t")[-1])==self.last_time_step-1]
		nodes_to_connect_new_layer = [node for node in layer_new.nodes if int(node.split("_t")[-1])==self.last_time_step]
		nodes_to_connect_basis_layer.sort()
		nodes_to_connect_new_layer.sort()

		self.graph.update(layer_new)


		for node_from,node_to in zip(nodes_to_connect_basis_layer,nodes_to_connect_new_layer):
			self.graph.add_edge(node_from,node_to,weight = 0,capacity = 1)

		self.last_time_step += 2
	


	def updated_name_block(self):
		layer = nx.relabel_nodes(self.block, lambda x: self.update_time_stamp_names(x,self.last_time_step))
		for node in layer.nodes:
			layer.node[node]['pos'] = (layer.node[node]['pos'][0],int(node.split("_t")[-1]))
		return layer


	def update_time_stamp_names(self,name,t):
		'''
		update the time stamp on the name, replacing it by the time t
		
		Parameters
		----------
		name : [type]
			[description]
		t : [type]
			[description]
		
		Returns
		-------
		[type]
			[description]
		'''
		name_original = name.split("_t")[0]
		t_original = int(name.split("_t")[-1])
		if t_original == 0:
			name_updated = name_original + "_t" + str(t)
		else:
			name_updated = name_original + "_t" + str(t+1)
		return name_updated


	def show(self, details = False):
		pos=nx.get_node_attributes(self.graph,'pos')
		nx.draw(self.graph,pos, with_labels = True)
		weights = nx.get_edge_attributes(self.graph,'weight')
		capacities = nx.get_edge_attributes(self.graph,'capacity')
		labels = {}
		if details:
			for key in weights.keys():
				labels[key] = (weights[key],capacities[key])
		_ = nx.draw_networkx_edge_labels(self.graph,pos,edge_labels=labels)