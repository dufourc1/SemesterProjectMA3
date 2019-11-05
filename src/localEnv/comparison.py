from lookuptable import LookUpTable
from agent import Agent
from qtable import QTable
from env import LocalEnv
from flatland.envs.observations import TreeObsForRailEnv
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_generators import complex_rail_generator
from flatland.envs.schedule_generators import complex_schedule_generator
from flatland.utils.rendertools import RenderTool
from visualization.graphic import draw_square
from datetime import datetime

import time
import matplotlib.pyplot as plt
import numpy as np


def choose_at_random(epsilon):
    decision = [0, 1]
    proba = [1-epsilon, epsilon]
    return np.random.choice(decision, p=proba)

def gen_env(number_agents, width, height, n_start_goal, seed):
    
    speed_ration_map = {1.: 0.25,  # Fast passenger train
                        1. / 2.: 0.25,  # Fast freight train
                        1. / 3.: 0.25,  # Slow commuter train
                        1. / 4.: 0.25}  # Slow freight train

    env = RailEnv(width=width,
                  height=height,
                  rail_generator=complex_rail_generator(nr_start_goal=n_start_goal,
                                                        nr_extra=3,
                                                        min_dist=6,
                                                        max_dist=99999,
                                                        seed = seed),
                  schedule_generator=complex_schedule_generator(speed_ratio_map=speed_ration_map),
                  number_of_agents=number_agents,
                  obs_builder_object=TreeObsForRailEnv(max_depth=5))
    
    env.reset()
    env.step(dict(zip(range(number_agents),[2]*number_agents)))
    
    return env

def get_current_state(env):
    result =[]
    for agent in env.agents:
        result.append((agent.position,agent.direction))
    return tuple(result)
    
number_agents = 4#np.random.randint(1,5)
width = 15#np.random.randint(3,20)
height = 15#np.random.randint(3,20)
n_start_goal = 5
seed = 1

env = gen_env(number_agents, width, height, n_start_goal, seed)

my_env = LocalEnv(env.rail.grid, env.agents)

n_episodes = 100
n_steps = 60 #(width + height) * number_agents
lap_time = datetime.now()

checkout_episode = 20

for episode in range(n_episodes):
    
    np.random.seed()
    my_env.restart_agents()
    my_env_current_state = my_env.get_current_state()
    current_state = get_current_state(env)
    
    if episode % checkout_episode == 0:
        print('episode:', episode)
        print('in', datetime.now() - lap_time)
        lap_time = datetime.now()
        renderer = RenderTool(env,agent_render_variant=3)
        renderer.reset()
    
    for step in range(n_steps):
        
        current_possible_actions = my_env.get_current_possible_actions()
        rand_index = np.random.choice(len(current_possible_actions))
        action = current_possible_actions[rand_index]
        
        if episode % checkout_episode == 0 :
            renderer.render_env(show=True, show_predictions=False, show_observations=False)
            time.sleep(0.5)
            
        if number_agents == 1 :
            reward, new_state, handles_done = my_env.step({0:action})
            env.step({0:action})
        else:
            reward, new_state, handles_done = my_env.step(dict(zip(range(number_agents),action)))
            env.step(dict(zip(range(number_agents),action)))
        
        tmp = my_env_current_state
        tmp_2 = current_state
        
        my_env_current_state = new_state
        current_state = get_current_state(env)
        
        for handle in range(number_agents):
            
            if not (env.agents[handle].position == None and my_env.agents[handle].position == my_env.agents[handle].target):            
                if env.agents[handle].position != my_env.agents[handle].position or env.agents[handle].direction != my_env.agents[handle].direction:
                    print("#################### EPISODE ", episode, " #######################")
                    print('  --------------------- step ', step, '  --------------------- action', action)
                    print('')
                    print(tmp, tmp_2)
                    print(my_env_current_state, current_state)
                    print('')
    
    if episode % checkout_episode == 0 :
        renderer.close_window()
        
    env = gen_env(number_agents, width, height, n_start_goal, seed)





renderer = RenderTool(env,agent_render_variant=3)
renderer.reset()
renderer.render_env(show=True, show_predictions=False, show_observations=False)


