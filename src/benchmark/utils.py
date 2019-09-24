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

#going towards this direction we must link to the node in the key
CONVENTION_TOWARDS = {
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


def cell_to_byte(cell_info):
	'''
	transform the information in the rail matrix of an RailEnv object into
	its byte representation
	Parameters
	----------
	cell_info : int
	
	Returns
	-------
	str
		byte representation of the int cell_info
	'''
	return bin(cell_info)[2:]


def get_direction(binary_4):
	results = []
	for i, elt in enumerate(binary_4):
		if elt == '1':
			results.append(trad_direction[i])
	return results



def identify_crossing(matrix_rail_element):
	'''
	return the possible transitions from the cell described by matrix_rail_element
	
	Parameters
	----------
	matrix_rail_element : int
		int converted byte representation of the possible transitions
	
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



	byte_representation = bin(int(matrix_rail_element))[2:]

	#get the possible actions based on from where the agent is arriving
	byte_north = byte_representation[0:4]
	byte_east = byte_representation[4:8]
	byte_south = byte_representation[8:12]
	byte_west = byte_representation[12:16]

	return {
		'N':get_direction(byte_north),
		'E': get_direction(byte_east),
		'S': get_direction(byte_south),
		'W':get_direction(byte_west)
	}
