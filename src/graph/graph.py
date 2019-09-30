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

class NetworkGraph(nx.DiGraph):
	'''
	implementation of the graph extracted from a flatland network
	'''

	def __init__(self, transition_matrix):
		super().__init__()
		self.superNodes = {}
		self.size = transition_matrix.shape
		self.build(transition_matrix)

	def build(self,transition_matrix):
		'''
		build the railway network based on the data in the transition matrix
		
		Parameters
		----------
		transition_matrix : numpy.ndarray
		'''

		for index, cell in np.ndenumerate(transition_matrix):
			if cell > 0:
				transition_dict = self.__get_transition_dictionnary(cell)
				superNode = SuperNode(index,transition_dict)
				self.superNodes[index] = superNode

				#incorporate the supernode into the bigger graph
				self.add_edges_from(superNode.edges())



	def __get_transition_dictionnary(self,cell_transition):
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

		#add minor correction for encpoint
		self.__correct_endpoint(results)

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
				if len(item) == 1:
					#check if opposite direction ('N' : ['S'])
					if OPPOSITE_DIRECTION[key][0] == item[0]:
						# change ('S':[] --> 'S':['S'])
						dic_transition[item[0]].append(item[0])
						#delete ('N':['S'] --> 'N':[])
						dic_transition[key] = []

		
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



class SuperNode(nx.DiGraph):
	'''
	node containing multiple 8 internal nodes representing the switches

	the different nodes are ['node.name_N_in','node.name_N_out','node.name_E_in','node.name_E_out','node.name_W_in','node.name_W_out','node.name_S_in','node.name_S_out']


	Here is a visual representation of the inner working of such a SuperNode

							North_out				South_in
								|						|


	west_out <--														<-- west_in

	east_in -->															--> est_out

								|						|
							North_in				South_out
	'''

	def __init__(self, index, transitions, nodes = ['N_in','N_out','E_in','E_out','W_in','W_out','S_in','S_out']):

		super().__init__()
		self.name = str(index)
		self.index = index
		
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
			node_base = self.name + "_" + in_direction + self.in_suffix

			for out_direction in out_directions:
				#get the name of the out node
				node_arrival =self.name + "_" + out_direction + self.out_suffix

				#add an edge between them
				self.add_edge(node_base,node_arrival)

	def show(self):
		'''
		pretty plotting of the internal nodes of the superNode
		'''
		pos_init = {
			'N_in':(1,1),
			'N_out':(1,4),
			'E_in': (0,2) ,
			'E_out':(3,2),
			'W_in':(3,3),
			'W_out':(0,3),
			'S_in':(2,4),
			'S_out':(2,1)
		}

		pos = {}
		#trick to add the proper nodes names
		for k,elt in pos_init.items():
			pos[self.name + "_" + k] = elt


		nx.draw(self,pos = pos, with_labels=True)
		plt.show()

