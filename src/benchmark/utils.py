import numpy as np
from flatland.core.grid.grid4 import Grid4Transitions


LISTE_TRANSITIONS =   [int('0000000000000000', 2),  # empty cell - Case 0
                       int('1000000000100000', 2),  # Case 1 - straight
                       int('1001001000100000', 2),  # Case 2 - simple switch
                       int('1000010000100001', 2),  # Case 3 - diamond drossing
                       int('1001011000100001', 2),  # Case 4 - single slip
                       int('1100110000110011', 2),  # Case 5 - double slip
                       int('0101001000000010', 2),  # Case 6 - symmetrical
                       int('0010000000000000', 2),  # Case 7 - dead end
                       int('0100000000000010', 2),  # Case 1b (8)  - simple turn right
                       int('0001001000000000', 2),  # Case 1c (9)  - simple turn left
                       int('1100000000100010', 2)]  # Case 2b (10) - simple switch mirrored



trad_direction = {
	0: 'N',
	1: 'E',
	2: 'S',
	3: 'W'
}

opposite_direction = {
	'S': 'N',
	'W': 'E',
	'N': 'S',
	'E': 'W'
}

#going towards this direction we must link to the node in the key
CONVENTION= {
	'W':'a',
	'S':'a',
	'N':'b',
	'E':'b'
}

#going from this direction we must link to the node in the key
CONVENTION_FROM = {
	'W':'b',
	'S':'b',
	'N':'a',
	'E':'a'
}

# CONVENTION_FROM = CONVENTION_TOWARDS


def get_node_direction(index,direction):
	if direction == 'N':
		return (index[0]-1,index[1])
	elif direction == 'S':
		return (index[0]+1,index[1])
	elif direction == 'E':
		return (index[0],index[1]+1)
	elif direction == 'W':
		return (index[0],index[1]-1)
	else:
		raise ValueError(f"direction not recognized: {direction}")

def tuple_to_str(x, filled = 4):
	'''
	(x,y) --> '000x000y'
	'''
	return str(x[0]).zfill(filled)+str(x[1]).zfill(filled)


def str_to_tuple(x_string):
	'''
	'000x000y' --> (x,y)
	'''
	return (int(x_string[0:4]),int(x_string[4:]))
	


def print_cell_transition(cell_transition):
	'''
	pretty printing of cell transition in 16 byte
	'''
	print("  NESW")
	print("N", format(cell_transition >> (3 * 4) & 0xF, '04b'))
	print("E", format(cell_transition >> (2 * 4) & 0xF, '04b'))
	print("S", format(cell_transition >> (1 * 4) & 0xF, '04b'))
	print("W", format(cell_transition >> (0 * 4) & 0xF, '04b'))



def get_direction(binary_4):
	results = []
	for i, elt in enumerate(binary_4):
		if elt == '1':
			results.append(trad_direction[i])
	return results




def identify_crossing(cell_transition):
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


	#correct for half_turn: indication of an endpoint, flatalnd mistake
	correct_endpoint(results)

	return results



def is_endpoint(dic_transition):
	#check if it is an endpoint by cheking if there is only one move authorized
	endpoint = True
	count = 0
	for key,item in dic_transition.items():
		if len(item) >0:
			count += 1

	if count > 1:
		endpoint = False

	return endpoint


def is_turn(dic_transition):
	if 'E' in dic_transition['N'] or 'W' in dic_transition['N'] or 'E' in dic_transition['S'] or 'W' in dic_transition['S']:
		return True
	else:
		return False

def change_endpoint(endpoint):
	if endpoint == 'a':
		return 'b'
	elif endpoint == 'b':
		return 'a'
	else:
		raise ValueError(f'expected a or b but got {endpoint} as argument')



def correct_endpoint(dic_transition):
	
	if is_endpoint(dic_transition):
		for key,item in dic_transition.items():
			if len(item) == 1:
				#check if opposite direction ('N' : ['S'])
				if opposite_direction[key][0] == item[0]:
					# change ('S':[] --> 'S':['S'])
					dic_transition[item[0]].append(item[0])
					#delete ('N':['S'] --> 'N':[])
					dic_transition[key] = []



def transitions_to_edges(cell_index,matrix_transition):
	'''
	given a transition matrix and an index returns a list of nodes to add by doing a one step ahead 
	to ensure proper connection of the graph_low_level
	
	Parameters
	----------
	cell_index : tuple
	matrix_transition : nd.array


	Return
	--------
	list of tuples representing the edges to add
	'''


	list_of_edges_to_add = []

	#get the name of the node
	name_node = tuple_to_str(cell_index)

	#get the dictionnary of transition
	results = identify_crossing(matrix_transition[cell_index])

	for key,goals in results.items():

		#get the departing node based on from where the train is coming
		e1 = name_node + CONVENTION[key]

		for goal in goals:

			#get the goal node based on where the train is going by default
			cell_receiving = get_node_direction(cell_index,goal)
			e2 = tuple_to_str(cell_receiving) +CONVENTION[goal]

			#check how the receiving node will behave 
			transitions_tmp = identify_crossing(matrix_transition[cell_receiving])

			#check that neither the receiving nor the sending node are endpoints
			list_of_edges_to_add.append((e1,e2))
			if is_turn(transitions_tmp):
				for tmp_departure, tmp_arrivals in transitions_tmp.items():

					#check that the arrival of the first node corresponds to the departure from the first one
					if goal not in tmp_arrivals:
						for elt in tmp_arrivals:
							if tmp_departure == goal and key != elt:# and key!=goal:

						
								list_of_edges_to_add.remove((e1,e2))
								e2 = e2[:-1] + CONVENTION[elt]
								list_of_edges_to_add.append((e1,e2))
								break
					
	return list_of_edges_to_add
	

		

		
def is_wrong_connections(index,graph,matrix_transition):
	'''
	take a graph and a cell as input and check if there are any defaults in the way the cells are wired in the turn cells

	the error is detected if it is possible for the agent to come back to the cell is was in two moves by following the oriented edges
	
	Parameters
	----------
	index : tuple
	graph : networkx instance of DiGraph
	'''

	name_node_in_graph = tuple_to_str(index)
	
	for start in ['a','b']:
		first_level = []
		second_level = []
		s = name_node_in_graph + start


		if is_turn(identify_crossing(matrix_transition[index])):
			for n in graph.neighbors(s):
				first_level.append(n)
				inter = []
				for n2 in graph.neighbors(n):
					inter.append(n2)
					if n2[:-1] == name_node_in_graph:
						return True,[s,n,n2]

		return False,[]


def swap_if_needed(cell_index,G,matrix_transition):

	node = tuple_to_str(cell_index)
	transitions = identify_crossing(matrix_transition[cell_index])
	if is_turn(transitions):

		#get all the in and out edges from the internal nodes
		in_edges_a = G.in_edges(node+'a')
		out_edges_a = G.out_edges(node+'a') 

		in_edges_b = G.in_edges(node+'b')
		out_edges_b = G.out_edges(node+'b')

		if len(in_edges_a) == 0 or len(in_edges_b) == 0 or len(out_edges_a) == 0 or len(out_edges_b)==0:

			#we swap
			neighbor_a = set([x[:-1] for x in G.neighbors(node+'a')])
			neighbor_b = set([x[:-1] for x in G.neighbors(node+'b')])
			common_n = neighbor_a.union(neighbor_b)


			swapped = False

			for n in common_n:
				if swapped: 
					break
				else:
					for elt1,elt2 in [('a','b'),('b','a')]:
						if (node+elt1,n+elt2) in G.edges and (n+elt1,node+elt2) in G.edges and not swapped:
							swapped = True
							#remove the old edges
							G.remove_edge(node+elt1,n+elt2)
							G.remove_edge(n+elt1,node+elt2)

							G.add_edge(n+elt1,node+elt1)
							G.add_edge(node+elt2,n+elt2)

	

def correct_double_edges_if_needed(graph_low_level,matrix):
	for node in G.nodes:
		for n in G.neighbors(node):
			if node in G.neighbor(n):
				#we got a double edge

				#deal with it 
				#we look at a and b for both super vertices, if one has an internal vertex with no in/out degree we
				#move the double edge to it 
				raise NotImplementedError("yeah fucking too long and no idea on how to proceed")

