import numpy as np 
def graphic_coordinate(i,j):
    """
    Translates matrix coordinates into graphic coordinate for rendertools functions
    """
    return np.array((j+0.5,-i-0.5))

def draw_path(env_renderer, path, size = 0.5, color = (255,0,0)):
    """
    Draws a path given a list 'path' and a Rendertools object 'env_renderer'
    """

    for coordinate in path:
        env_renderer._draw_square(graphic_coordinate(coordinate[0],coordinate[1]), size, color)

def draw_multiple_paths(env_renderer, paths):
    """
    Draws multiple paths by recursive call to draw_path from list of list 'paths'. Size and color
    of a given path are attributed as a function of the index of that path in 'paths'.
    """
#    number_of_paths = len(paths)
#    HSV_tuples = [(x*1.0/number_of_paths, 0.5, 0.5) for x in range(number_of_paths)]
#    RGB_tuples = list(map(lambda x: colorsys.hsv_to_rgb(*x), HSV_tuples))
    
    rgb_list = [(255,0,0),(172,0,0),(89,0,0),
                (0,255,0),(0,172,0),(0,89,0),
                (0,0,255),(0,0,172),(0,0,89),
                (255,255,0),(255,172,0),(255,89,0),(255,0,255),(255,0,172),(255,0,89),
                (172,255,0),(172,172,0),(172,89,0),(172,0,255),(172,0,172),(172,0,89),
                (89,255,0),(89,172,0),(89,89,0),(89,0,255),(89,0,172),(89,0,89)]
    for index, path in enumerate(paths):
        draw_path(env_renderer,
                  path,
                  size = 1 / (index + 1.1),
                  color = rgb_list[index])
                  
                  
#                  ((255/number_of_paths)* index, 0, (255/number_of_paths)*(number_of_paths - index)))