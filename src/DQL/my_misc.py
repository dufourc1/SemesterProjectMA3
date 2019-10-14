def get_shortest_paths_list(dictionnary):
    """
    Returns the shortest paths from envs.rail_env_shortest_paths.get_shortest_paths as a list of list.
    The main use for this function right now is to get the path as a list to draw it through my functions in
    vizualisation.
    """
    list_of_paths = []
    
    def get_path_list_from_WalkingElement_list(list_):
        result = []
        for element in list_:
            result.append(element.position)
        return result
        
    for key in dictionnary:
        list_of_paths.append(get_path_list_from_WalkingElement_list(dictionnary[key]))
    
    return list_of_paths