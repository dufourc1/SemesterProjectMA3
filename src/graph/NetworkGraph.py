import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

# GLOBAL VARIBALES
TRAD_DIRECTION = {
	0: 'N',
	1: 'E',
	2: 'S',
	3: 'W'
}

OPPOSITE_DIRECTION = {
	'S': 'N',
	'W': 'E',
	'N': 'S',
	'E': 'W'
}


#jitter for pretty plotting
JITTER = {
			'S_in':[1,1],
			'N_out':[1,4],
			'W_in': [0,2] ,
			'E_out':[3,2],
			'E_in':[3,3],
			'W_out':[0,3],
			'N_in':[2,4],
			'S_out':[2,1]
}


def parse_tuple_from_txt(tuple_str):
    interest = tuple_str.split("_")[0]
    interest_left = interest.split("(")[1].split(",")[0]
    interest_right = interest.split(")")[0].split(",")[1]
    return (int(interest_left),int(interest_right))



class NetworkGraph(nx.DiGraph):
	'''
	implementation of the graph extracted from a flatland network
	'''

	def __init__(self, transition_matrix,sources = [],sinks = []):

		super().__init__()
		self.superNodes = {}
		self.position_constraints = []
		self.swapping_constraints = {}
		assert len(sources) == len(sinks), 'sources and sinks are supposed to have same lengths'
		self.sources = sources
		self.sinks = sinks
		self.size = transition_matrix.shape
		self.graph_connectivity = nx.DiGraph()
		self.build(transition_matrix)
		self.swapping_constraints_liste = [x for _,x in self.swapping_constraints.items()]
		


	def build(self,transition_matrix):
		'''
		build the railway network based on the data in the transition matrix
		
		Parameters
		----------
		transition_matrix : numpy.ndarray
		'''

		#initialize the super nodes
		self.__build_SuperNodes_list(transition_matrix)

		#build the edges between the super nodes
		self.__link_SuperNodes()

		#print a warning if the sanity check was not passed
		self.sanity_check()

	def sanity_check(self):
		'''
		perform a simple sanity check on the graph extracted from the environment
		by checking for cycle in the directed graph
		
		'''
		try:
			cycles = nx.find_cycle(self)
			#print("cycles detected in NetworkGraph, this may be due to the fact that endpoint can be used to do 180 turn")
		except(nx.NetworkXNoCycle):
			pass
		
		
	def __build_SuperNodes_list(self,transition_matrix):
		'''
		build the list of SuperNodes, instanciate the connection in them correctly and compute the 
		connectivity graph but do not link super nodes together
		
		Parameters
		----------
		transition_matrix : numpy.ndarray
		'''
		for index, cell in np.ndenumerate(transition_matrix):
			if cell > 0:

				#get the transition dict for this class
				transition_dict = self.__get_transition_dictionnary(cell)

				#initialize the superNode corresponding to this cell
				superNode = SuperNode(index,transition_dict)
				self.position_constraints.append(superNode.get_constraints())
				self.superNodes[index] = superNode
						

				#add the nodes with the data to the graph
				#incorporate the supernode edges into the bigger graph
				self.add_nodes_from(superNode.nodes)
				self.add_edges_from(superNode.edges)
				

				self.graph_connectivity.add_edges_from(self.__get_edges_connectivity(index,
																					transition_dict))



	def __get_edges_connectivity(self,index,transition_dict):
		'''
		get the edges for the connectivity graph based on one cell
		'''
		edges = []
		for _,directions in transition_dict.items():
			for direction in directions:
				if direction == 'N':
					edges.append((index,(index[0]-1,index[1])))
				elif direction == 'S':
					edges.append((index,(index[0]+1,index[1])))
				elif direction == 'E':
					edges.append((index,(index[0],index[1]+1)))
				elif direction == 'W':
					edges.append((index,(index[0],index[1]-1)))
				else:
					raise ValueError(f"direction not recognized: {direction}")

		return edges


	def __link_SuperNodes(self):
		'''
		connects the superNodes together
		'''
		for node in self.graph_connectivity.nodes : 
		

			#get the neighbors of the node
			neighbors = self.graph_connectivity.neighbors(node)

			for n in neighbors:
				#get the neighbor and connect it to the first superNode
				self.connect_supernodes(node,n)


	def connect_supernodes(self, index1,index2):

		try: 
			
			superNode_from = self.get_superNode_at(index1)
			superNode_to = self.get_superNode_at(index2)
			if superNode_from.name == superNode_to.name:
				raise ValueError(f'cannot link the same node {superNode_from},{superNode_to}')
			#get the relative position of the two cells

			if np.linalg.norm(np.array(index1)-np.array(index2)) > 1:
				raise ValueError(f'cells are two far apart and ',
									f'should not be connected: {index1}, {index2}')
			
			#connection is on the y axis
			if index1[1] != index2[1]:

				#cell1 is on the left of cell 2
				if index1[1]<index2[1]:
					connection_out = 'E_out'
					connection_in = 'W_in'

				#cell1 is on the right of cell2
				else:
					connection_out = 'W_out'
					connection_in = 'E_in'

			#connection is on the x axis
			elif index1[0] != index2[0]:
				
				#cell1 is above cell2
				if index1[0]<index2[0]:
					connection_in = 'N_in'
					connection_out = 'S_out'
				#cell2 is below cell2
				else:
					connection_in = 'S_in'
					connection_out = 'N_out'

			else:
				raise ValueError(f"trying to connect the same superNode with itself {index1}")

			edge = (superNode_from.name+"_"+connection_out,superNode_to.name +"_"+connection_in)

			if (index1,index2) not in self.swapping_constraints.keys():
				if (index2,index1) not in self.swapping_constraints.keys():
					self.swapping_constraints[(index1,index2)] = [edge]
				else:
					self.swapping_constraints[(index2,index1)].append(edge)
			else:
				self.swapping_constraints[(index1,index2)] = [edge]

			#actual connection
			self.add_edge(*edge)
		except:
			#pass
			print(f' warning on connections between {index1} and {index2}')
				


	def __get_transition_dictionnary(self,cell_transition, supernode = False):
		'''
		return the possible transitions from the cell described by matrix_rail_element
		
		Parameters
		----------
		matrix_rail_element : int
			value of the rail matrix
		
		Returns
		-------
		dict
		{
			'N':['S','E'],
			'E':[],
			'S':['N'],
			'W':['E']
		}
			
		'''
		
		#conversion from binary to list of directions
		def get_direction(binary_4):
			results = []
			for i, elt in enumerate(binary_4):
				if elt == '1':
					results.append(TRAD_DIRECTION[i])
			return results


		cell_transition = int(cell_transition)
		#get the possible actions of the train based on its direction
		N = format(cell_transition >> (3 * 4) & 0xF, '04b')
		E = format(cell_transition >> (2 * 4) & 0xF, '04b')
		S = format(cell_transition >> (1 * 4) & 0xF, '04b')
		W = format(cell_transition >> (0 * 4) & 0xF, '04b')

		results = {
			'N':get_direction(N),
			'E': get_direction(E),
			'S': get_direction(S),
			'W':get_direction(W)
		}

		#add minor correction for endpoint
		if supernode:
			results = self.__correct_endpoint(results)

		return results


	def __is_cell_endpoint(self,dic_transition):
		'''
		check if it is an endpoint by cheking if there is only one move authorized
		'''
		endpoint = True
		count = 0
		for key,item in dic_transition.items():
			if len(item) >0:
				count += 1

		if count > 1:
			endpoint = False

		return endpoint

	def __correct_endpoint(self,dic_transition):
		'''
		correct the strange notation in the endpoints direction
		'''
		if self.__is_cell_endpoint(dic_transition):
			for key,item in dic_transition.items():
				if len(item) == 1  :
					if key != 'N' and key != 'S':
						#check if opposite direction ('N' : ['S'])
						if OPPOSITE_DIRECTION[key][0] == item[0]:
							# change ('S':[] --> 'S':['S'])
							dic_transition[item[0]].append(item[0])
							#delete ('N':['S'] --> 'N':[])
							dic_transition[key] = []
					else:
						#check if opposite direction ('N' : ['S'])
						if OPPOSITE_DIRECTION[key][0] == item[0]:
							# change ('N':['S'] --> 'S':['N'])
							dic_transition[key] = [key]
			# dic_transition = {
			# 								'N':[],
			# 								'E': [],
			# 								'S': [],
			# 								'W':[]
			# 							}
		return dic_transition

	def get_cell_position_node(self,node):
		'''
		return the index of the cell where node belongs as a tuple
		
		Parameters
		----------
		node : str
			name of the node in the graph
		'''
		
		inter = node.split("_")[0]
		return (int(inter[1]),int(inter[4]))

		
		
	def get_superNode_at(self,index):
		'''
		return the superNode at position index = (x,y) in the original matrix
		
		Parameters
		----------
		index : tuple
		
		Returns
		-------
		SuperNode
			supernode at position index = (x,y)
		'''
		return self.superNodes[index]

	def position(self,node, jitter = 0.1):
		'''
		given a node of the graph, 
		return its position for pretty plotting
		
		Parameters
		----------
		node : node of nx.DiGraph
			obtained from G.ndoes()
		'''
		# print(node)
		#get the cell index
		cell_index = parse_tuple_from_txt(node)
		#get the "port"
		subname = "_".join(node.split("_")[-2:])

		#comput the position
		position_node = (cell_index[0] - jitter*JITTER[subname][1], 
						cell_index[1] + jitter*JITTER[subname][0])
		# print(position_node)
		# print("\n")
		return (position_node[1],-position_node[0])


	def show(self, jitter = 0.1, title = None):		
		'''
		pretty plotting of the network graph
		'''
		plt.figure(figsize=(50,50))
		node_color = 'steel_blue'
		pos = dict( (n, self.position(n, jitter)) for n in self.nodes() )
		nx.draw(self ,pos,with_labels = False, node_size=50)
		if title is not None:
			plt.savefig(title)
		plt.show()

	def getPositionConstraints(self):
		return self.position_constraints

	def getSwappingConstraints(self):
		return self.swapping_constraints_liste

class SuperNode(nx.DiGraph):
	'''
	node containing multiple 8 internal nodes representing the switches, but not allowing 180 turn

	the different nodes are ['node.name_N_in','node.name_N_out','node.name_E_in',
							'node.name_E_out','node.name_W_in','node.name_W_out',
							'node.name_S_in','node.name_S_out']


	Here is a visual representation of the inner working of such a SuperNode

				North_out	Norht_in
					
		west_out				 	east_in

		west_in 					east_out		

				South_in	South_out
	'''

	def __init__(self, index, transitions, nodes = ['N_in','N_out','E_in','E_out',
													'W_in','W_out','S_in','S_out']):

		super().__init__()
		self.name = str(index)
		self.index = index
		self.constraints = []
		
		#constant defined if changes in the structure of the incoming matrix
		self.in_suffix = '_in'
		self.out_suffix = '_out'

		self.add_nodes_from([self.name +"_"+ x for x in nodes])
		self.add_edges_from_transition(transitions)
		

	def add_edges_from_transition(self,transitions):
		'''
		add edges from a transition dictionnary
		
		Parameters
		----------
		transitions : dict
			{
				'N':['N','E'],
				'S':['S'],
				'E':[],
				'W':[]

			}
		'''

		for in_direction,out_directions in transitions.items():
			#get the name of the entry node
			node_base = self.name + "_" + OPPOSITE_DIRECTION[in_direction] + self.in_suffix

			for out_direction in out_directions:
				#uncomment this line to forbid 180 turn at endpoint
				#if self.__check_180_turn(in_direction,out_direction):
				if True:
					#get the name of the out node
					node_arrival =self.name + "_" + out_direction + self.out_suffix

					#add an edge between them
					self.constraints.append((node_base,node_arrival))
					self.add_edge(node_base,node_arrival)

	def update_node_attribute(self,annotations):
		for node in self.nodes:
			for key,item in annotations.items():
				if item.startswith('source') and node.endswith('out'):
					self.node[node][key] = item
				elif item.startswith("sink") and node.endswith('in'):
					self.node[node][key] = item
				elif item == 'transshipment':
					self.node[node][key] = item

	def __check_180_turn(self,in_direction,out_direction):
		'''
		check if the transition cell would allow a 180° turn 
		
		Parameters
		----------
		in_direction : str
		out_direction : str
		
		Returns
		-------
		bool
		'''
		return out_direction != OPPOSITE_DIRECTION[in_direction]

	def show(self, trajectories= None):
		'''
		pretty plotting of the internal nodes of the superNode
		'''

		if trajectories is not None:
			raise NotImplementedError("implement this visu moron")
		else:
			for edge in self.edges:
				# add color to edge (black by default)
				raise NotImplementedError("implement this visu moron")
			
		pos = {}
		labels = {}
		#trick to add the proper nodes names
		for k,elt in JITTER.items():
			pos[self.name + "_" + k] = elt
			labels[self.name + "_" + k] = k

		options = {
			'pos':pos,
			'alpha': 0.8,
			'with_labels': True,
			'labels':labels,
			'node_size': 1200,
			'width': 3,
			'arrowsize':10,
		}

		nx.draw(self,**options)
		plt.show()

	def get_constraints(self):
		return self.constraints
