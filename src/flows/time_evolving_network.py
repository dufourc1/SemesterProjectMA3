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

		self.graph = nx.DiGraph()
		self.last_time_step = 0


		#extract the nodes
		self.basis_layer = 	self.build_base_layer(incoming_graph_data = incoming_graph_data,
													default_capacity = default_capacity,
													default_weight = default_weight,
													waiting_cost = waiting_cost,
													waiting_capacity = waiting_capacity)

		# self.intermediate_layer = self.build_intermediate_layer(incoming_graph_data,
		# 														intermediate_weight,
		# 														intermediate_capacity)

		self.graph.update(self.basis_layer)




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
		return basis_layer

	def build_intermediate_layer(self,
								incoming_graph_data,
								intermediate_weight,
								intermediate_capacity):

		#do stuff
		self.last_time_step += 1
		raise NotImplemented

			

	def build_new_depth_network(self,type_network = 'basis'):
		'''
		take the layer and update the names of the nodes to make it ready to be added 
		in top of the originaly existing graph, then add it to the already existing network
		
		Parameters
		----------
		type_network : str, optional
			basis layer or intermediate layer, by default 'basis'
		'''
		if type_network == 'basis':
			layer_inter = nx.relabel_nodes(basis_layer, lambda x: self.update_time_stamp_names(x,self.last_time_step))
			self.last_time_step += 2
			raise NotImplementedError
		elif type_network == 'intermediate':
			# do stuff
			self.last_time_step += 1
			raise NotImplementedError
	

	def update_time_stamp_names(self,name,t):
		name_original = name.split("_t")[0]
		t_original = int(name.split("_t")[-1])
		if t_original == 0:
			name_updated = name_original + "_t" + str(t)
		else:
			name_updated = name_original + "_t" + str(t+1)
		return name_updated


	def show(self):
		pos=nx.get_node_attributes(self.graph,'pos')
		nx.draw(self.graph,pos, with_labels = True)
		weights = nx.get_edge_attributes(self.graph,'weight')
		capacities = nx.get_edge_attributes(self.graph,'capacity')
		labels = {}
		for key in weights.keys():
			labels[key] = (weights[key],capacities[key])
		_ = nx.draw_networkx_edge_labels(self.graph,pos,edge_labels=labels)