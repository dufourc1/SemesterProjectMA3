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


import matplotlib.pyplot as plt
import numpy as np

def moving_average(a, n=3) :
    ret = np.cumsum(a, dtype=float)
    ret[n:] = ret[n:] - ret[:-n]
    return ret[n - 1:] / n


def choose_at_random(epsilon):
    decision = [0, 1]
    proba = [1-epsilon, epsilon]
    return np.random.choice(decision, p=proba)

def run(env,
        n_episodes,
        n_steps,
        initial_value = 0,
        learning_rate = 0.8,
        gamma = 0.9,
        epsilon = 0.1):
    
    env.reset()
    number_agents = len(env.agents)
    env.step(dict(zip(range(number_agents),[2]*number_agents)))
    
    my_env = LocalEnv(env.rail.grid, env.agents)
    initial_state = my_env.initial_state
    qtable = QTable(number_agents, initial_state, initial_value, gamma, learning_rate )
    
    lap_time = datetime.now()

    steps_per_episode = []
    
    for episode in range(n_episodes):
        
        np.random.seed()
        my_env.restart_agents()
        current_state = my_env.get_current_state()
        
        if episode % 100 == 0:
            print('episode:', episode)
            print('in', datetime.now() - lap_time)
            lap_time = datetime.now()
        
        count = 0
        for step in range(n_steps):
            
            
            if choose_at_random(epsilon):
                current_possible_actions = my_env.get_current_possible_actions()
                rand_index = np.random.choice(len(current_possible_actions))
                action = current_possible_actions[rand_index]
            else:
                action = qtable.get_max_action(current_state)
            
            if number_agents == 1 :
                reward, new_state, handles_done = my_env.step({0:action})
            else:
                reward, new_state, handles_done = my_env.step(dict(zip(range(number_agents),action)))
            
            count+=1
            
            if len(handles_done) == number_agents:
                break
            
#            if number_agents != 1 :
#                action = list(action)
#                for handle in handles_done:
#                    action[handle] = 4
#                action = tuple(action)
#                
#            print('')
#            print(current_state)
#            print(action)
#            print(new_state)
            qtable.update_table(current_state, action, new_state, reward)
            current_state = new_state
        
        steps_per_episode.append(count)

    return steps_per_episode, my_env, qtable
#%%

number_agents = 3#np.random.randint(1,5)
width = 10#np.random.randint(3,20)
height = 10#np.random.randint(3,20)
n_start_goal = 5
seed = 1


env = RailEnv(width=width,
              height=height,
              rail_generator=complex_rail_generator(nr_start_goal=n_start_goal,
                                                    nr_extra=3,
                                                    min_dist=6,
                                                    max_dist=99999,
                                                    seed = seed),
              schedule_generator=complex_schedule_generator(),
              number_of_agents=number_agents,
              obs_builder_object=TreeObsForRailEnv(max_depth=5))
              



n_episodes = 6000
n_steps = (width + height) * number_agents


steps_per_episode, my_env, qtable= run(env,
        n_episodes,
        n_steps,
        initial_value = 0,
        learning_rate = 0.8,
        gamma = 0.95,
        epsilon = 0.1)


renderer = RenderTool(env,agent_render_variant=3)
renderer.reset()
renderer.render_env(show=True, show_predictions=False, show_observations=False)

steps_per_episode = np.array(steps_per_episode)
plt.plot(moving_average(steps_per_episode,1000))


