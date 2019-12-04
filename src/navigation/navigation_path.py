import numpy as np
import time
from src.visualization.graphic import draw_multiple_paths

def l2_norm(v, u):
    """
    computes L² norm of vector difference
    """
    
    return np.linalg.norm(v - u)

def action_to_next_cell(current_cell, next_cell,direction):
    """
    This function uses matrix coordinate encoding of the grid.
    Returns the action necessary to go from current_cell to next_cell given the direction of the agent 
    and the new direction of the agent.
    direction:
        0 = going North
        1 = going East
        2 = going South
        3 = going West
    """    
    if current_cell == next_cell:
        return 4, direction
    
    if direction == 0 or direction == 2:
        if current_cell[1] == next_cell[1]:
            return 2, direction
        if current_cell[1]+1 == next_cell[1]:
            if direction == 0:
                return 3, 1
            else: return 1, 1
        if current_cell[1]-1 == next_cell[1]:
            if direction == 0:
                return 1, 3
            else: return 3, 3
        
    
    if direction == 1 or direction == 3:
        if current_cell[0] == next_cell[0]:
            return 2, direction
        if current_cell[0]+1 == next_cell[0]:
            if direction == 1:
                return 3, 2
            else: return 1, 2 
        if current_cell[0]-1 == next_cell[0]:
            if direction == 1:
                return 1, 0
            else: return 3, 0 
        
def actions_for_path(path,direction):
    """
    This function uses matrix coordinate encoding of the grid.
    Returns a list of actions in order to walk the path, constructed by recursive calls to action_to_next_cell
    """
    
    actions = []
    for k in range(len(path)-1):
        
        if l2_norm(np.array(path[k]),np.array(path[k+1])) in (0,1):
            action, new_direction = action_to_next_cell(path[k],path[k+1],direction)
            
            #This bit is added to correct the direction after the first step, given that oftentimes, 
            #the train starts facing a dead-end, in which case, taking action '2' makes the train do a 180 turn 
            #and a step forward as well, thus flipping the direction which is not handled in action_to_next_cell
            if k == 0:
                if direction == 0 and path[k][0]+1 == path[k+1][0]:
                    new_direction = 2
                if direction == 2 and path[k][0]-1 == path[k+1][0]:
                    new_direction = 0
                if direction == 1 and path[k][1]-1 == path[k+1][1]:
                    new_direction = 3
                if direction == 3 and path[k][1]+1 == path[k+1][1]:
                    new_direction = 1


            actions.append(action)
            direction = new_direction


        else:
            print('invalid path entry, at coordinates: ' + str(k)+ ', ' + str(k+1))
            return actions.append(-1)
        
    return actions

def walk_path(env, env_renderer, path, agent_handle):
    """
    This function takes RailEnv object 'env' and RenderTool object 'env_renderer', gets the actions to walk 
    a path and makes the given agent walk the path, updating the graphical interface at each step
    """
    
    actions = actions_for_path(path, env.agents[agent_handle].direction)
    
    for action in actions:
        env.step({agent_handle : action})
        env_renderer.render_env(show=True, show_predictions=False, show_observations=False)
        time.sleep(0.5)

def walk_many_paths(env, env_renderer, paths, draw = False):
    """
    This functions that a list of paths and makes agents walk their own path simultaneously (the list is assumed to be
    ordered i.e. paths[k] is the path of agent k.)
    
    
    For now this assumes no collisions.
    """
    if draw == True:
        draw_multiple_paths(env_renderer, paths)
    
    actions_list = [actions_for_path(path, env.agents[k].direction) for k, path in enumerate(paths)]
    all_done = False

    start_index = setup_env(env,paths,actions_list)

   

    i = 0
    while all_done == False:
        
        #done here means an agent has made as many steps as was specified in its actions_for_path
        agents_done = 0
        actions_dict = {}
        
        for k in range(start_index,len(paths)):
            
            if  i < len(actions_list[k]):
                actions_dict[k] = actions_list[k][i]
            else:
                agents_done += 1
        
        if agents_done == len(paths):
            all_done = True
        env.step(actions_dict)
        check_position(i+1,env,paths)
        env_renderer.render_env(show=True, show_predictions=False, show_observations=False)
        time.sleep(0.03)
        i += 1


def check_position(time,env,paths):
    for agent,path in enumerate(paths):
        if  time < len(path) and  env.agents[agent].status != 3 and path[time] != env.agents[agent].position:
            print(f"Error ! agent  {agent} is supposed to be at cell {path[time]} but is at {env.agents[agent].position} at time {time}")


def setup_env(env,paths,actions_list,renderer = None):


    #try first step for everyone 
    _ = env.step({i:1 for i in range(len(paths))})
    if renderer is not None:
        renderer.render_env(show=True, show_predictions=False, show_observations=False)
    return 0
    # agents_to_remove = []
    # for agent in range(len(paths)):
    #     if env.agents[agent].status == 0:
    #         agents_to_remove.append(agent)
    
    # if len(agents_to_remove) == 0:
    #     return 0

    # dict_action = {k:4 for k in agents_to_remove}
    # dict_action.update({k:actions_list[k][0] for k in range(len(paths)) if k not in agents_to_remove})
    # env.step(dict_action)

    # dict_action = {k:1 for k in agents_to_remove}
    # dict_action.update({k:4 for k in range(len(paths)) if k not in agents_to_remove})
    # env.step(dict_action)
    # dict_action = {k:actions_list[k][0] for k in agents_to_remove}
    # dict_action.update({k:4 for k in range(len(paths)) if k not in agents_to_remove})
    # env.step(dict_action)

    # return 1
    
    
    
    
    
    
    
    
        
        