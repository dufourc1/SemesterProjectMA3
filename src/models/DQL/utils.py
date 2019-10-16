import numpy as np

def get_rail_coordinates(env):
    
    """
    Returns a list of grid coordinates corresponding to cells where there is a railway
    """
    rail_coordinates = []
    non_zero = np.nonzero(env.rail.grid)
    for index in range(len(non_zero[0])):
        rail_coordinates.append((non_zero[0][index],non_zero[1][index]))
    
    return rail_coordinates