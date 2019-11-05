import random
import time
import numpy as np
import matplotlib.pyplot as plt
from flatland.envs.observations import TreeObsForRailEnv
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_generators import complex_rail_generator
from flatland.envs.schedule_generators import complex_schedule_generator
from flatland.utils.rendertools import RenderTool
#from flatland.envs.rail_env_shortest_paths import get_shortest_paths
#from src.visualization.graphic import graphic_coordinate,draw_path,draw_multiple_paths
#from src.navigation.navigation_path import actions_for_path,walk_path,walk_many_paths
#from utils import get_shortest_paths_list
from datetime import datetime
from itertools import product

def moving_average(a, n=3) :
    ret = np.cumsum(a, dtype=float)
    ret[n:] = ret[n:] - ret[:-n]
    return ret[n - 1:] / n


#%%

def choose_at_random(epsilon):
    decision = [0, 1]
    proba = [1-epsilon, epsilon]
    return np.random.choice(decision, p=proba)

def get_agent_state(env, handle, start = False):
    if start == True:
        return((env.agents[handle].initial_position[0],env.agents[handle].initial_position[1],env.agents[handle].direction))
    else:
        return((env.agents[handle].position[0],env.agents[handle].position[1],env.agents[handle].direction))

def get_agent_states(env, start = False):
    if len(env.agents) == 1:
        return get_agent_state(env, 0, start)
    positions_list = []
    for handle in range(len(env.agents)):
        positions_list.append(get_agent_state(env, handle,start))
    return tuple(positions_list)

def get_product_set(iterables):
    if len(iterables) == 1 :
        return iterables[0]
    else:
        return list(product(*iterables))

#%%
class Qtable():
    
    def __init__(self, env, init_val, learning_rate, gamma, n_actions = 5, n_directions = 4):
        self.env = env
        self.n_agents = len(self.env.agents)
        if self.n_agents == 1:
            self.starting_positions = tuple([self.env.agents[0].initial_position[0], self.env.agents[0].initial_position[1], self.env.agents[0].direction])   
        else:     
            self.starting_positions = tuple([tuple([agent.initial_position[0],agent.initial_position[1],agent.direction]) for agent in self.env.agents])
        self.target_locations = [ agent.target for agent in self.env.agents]
        self.n_actions = n_actions
        self.init_v = init_val
        self.lr = learning_rate
        self.y = gamma
        self.dico = {get_agent_states(self.env, start = True) : 0}
        if len(env.agents) == 1:
            self.Q_1 = np.array([[{2 : 0}]])
            self.Q_2 = np.array([[{2 : 0}]])
            self.Q = np.array([[{2 : 0}]])
        else:
            self.Q_1 = np.array([[{tuple([2]*self.n_agents) : 0}]])
            self.Q_2 = np.array([[{tuple([2]*self.n_agents) : 0}]])
            self.Q = np.array([[{tuple([2]*self.n_agents) : 0}]])
    
    def get_agent_next_step(self, handle):
        #NESW
        possible_agent_actions = []
        new_agent_states = []

        for action in range(self.n_actions-1):
            cell_free, \
            new_cell_valid, \
            new_direction, \
            new_position, \
            transition_valid = self.env._check_action_on_agent(action, self.env.agents[handle])
            
            if transition_valid in [True, 1]:
                possible_agent_actions.append(action)
                new_agent_states.append(tuple(list(new_position) + [new_direction]))
                
        #action 4 is badly handled : bad next position
        possible_agent_actions.append(4)
        new_agent_states.append(get_agent_state(self.env, handle))      
        
        return possible_agent_actions, new_agent_states

    def get_next_step(self, state):
        #NESW
        possible_actions = []
        new_states = []

        for handle in range(self.n_agents):
            possible_agent_actions, new_agent_states = self.get_agent_next_step(handle)
            possible_actions.append(possible_agent_actions)
            new_states.append(new_agent_states)        
        
        possible_actions = get_product_set(possible_actions)
        new_states = get_product_set(new_states)
            
        return possible_actions, new_states
        

    def add_row(self, state):
        possible_actions, new_states = self.get_next_step(state)
        action_dict = dict(zip(possible_actions,[self.init_v]*len(possible_actions)))

        self.Q = np.vstack((self.Q, action_dict))
        self.Q_1 = np.vstack((self.Q_1, action_dict))
        self.Q_2 = np.vstack((self.Q_2, action_dict))

        return len(self.Q)-1        
    
    def update(self, state, state_, action, reward):
        if state_ not in self.dico.keys():
            self.dico[state_] = self.add_row(state_)       
                 
        choice = np.random.choice([1,2])
        if choice == 1:
            Q_1_max_value_action_for_state_ = max(self.Q_1[self.dico[state_]][0], key = self.Q_1[self.dico[state_]][0].get) 
            self.Q_1[self.dico[state]][0][action] += self.lr * (reward + self.y * \
                                                    self.Q_2[self.dico[state_]][0][Q_1_max_value_action_for_state_] \
                                                    - self.Q_1[self.dico[state]][0][action])
        else:
            Q_2_max_value_action_for_state_ = max(self.Q_2[self.dico[state_]][0], key = self.Q_2[self.dico[state_]][0].get) 
            self.Q_2[self.dico[state]][0][action] += self.lr * (reward + self.y * \
                                                    self.Q_1[self.dico[state_]][0][Q_2_max_value_action_for_state_] \
                                                    - self.Q_2[self.dico[state]][0][action])
        
        row_Q_1 = self.Q_1[self.dico[state]][0]
        row_Q_2 = self.Q_2[self.dico[state]][0]
        row_Q = {}
        for key in row_Q_1.keys():
            row_Q[key] = (row_Q_1[key] + row_Q_2[key])/2
        
        self.Q[self.dico[state]][0] = row_Q
        
    def valid_actions(self, state):
        row_Q_1 = self.Q_1[self.dico[state]][0]
        return list(row_Q_1.keys())
        
    def find_max_action(self, state):
        return max(self.Q[self.dico[state]][0], key = self.Q[self.dico[state]][0].get)
    
    def get_policy_paths(self, env):
        self.env = env
        paths = []
        positions = self.starting_positions
        paths.append(positions)
        env.step(dict(zip(range(self.n_agents),[2]*self.n_agents)))
        arrived = False
        while not arrived : 

            max_action = self.find_max_action(positions)
            
            print(positions)
            print(max_action)

            possible_action, new_states = self.get_next_step(positions)
            positions = new_states[possible_action.index(max_action)]
            paths.append(positions)
            
            if number_agents == 1:
                action_dict = {0:max_action}
            else:
                action_dict = dict(zip(range(self.n_agents),max_action))

            obs, all_rewards, status, _= self.env.step(action_dict)        
            
            for handle in range(self.n_agents):
                if self.env.agents[handle].position != self.env.agents[handle].target:
                    arrived = False
                    break
                else:
                    arrived = True
                    
        return paths
    
def create_env(number_agents,width,height,n_start_goal,seed):
    env = RailEnv(width=width,
              height=height,
              rail_generator=complex_rail_generator(nr_start_goal=n_start_goal,
                                                    nr_extra=1,
                                                    min_dist=8,
                                                    max_dist=99999,
                                                    seed = seed),
              schedule_generator=complex_schedule_generator(),
              number_of_agents=number_agents)
    
    return env   

def get_delta(Q_old, Q_old_index, Q, Q_index):


    index_actions = get_product_set([[0,1,2,3,4]] * number_agents)
    index_actions = dict(zip(index_actions, list(range(len(index_actions)))))

    #Build newly formatted Q and Q_old
    Q_matrix = np.zeros((len(Q_index),len(index_actions)))
    Q_matrix_old = np.zeros((len(Q_old_index),len(index_actions)))
    delta = np.zeros((len(Q_index),len(index_actions)))
    #update Q_old
    for state in Q_old_index.keys():
        for action in index_actions.keys():
            if action in Q_old[Q_old_index[state]][0].keys() :
                Q_matrix_old[Q_old_index[state], index_actions[action]] = Q_old[Q_old_index[state]][0][action]
    
    #update Q
    for state in Q_index.keys():
        for action in index_actions.keys():
            if action in Q[Q_index[state]][0].keys() :
                Q_matrix[Q_index[state], index_actions[action]] = Q[Q_index[state]][0][action]

    #Compute difference               
    for state in Q_old_index.keys():
        for action in index_actions.keys():
            delta[Q_old_index[state],index_actions[action]] = Q_matrix[Q_old_index[state],index_actions[action]] - Q_matrix_old[Q_old_index[state],index_actions[action]] 
    
    if np.count_nonzero(delta) != 0:
        return np.linalg.norm(delta,np.inf/len(index_actions))
    else: 
        return -1

def run(number_agents,
            width,height,
            n_start_goal,
            seed,
            n_episodes,
            n_steps,
            initial_value = 0,
            learning_rate = 0.8,
            gamma = 0.9,
            epsilon = 0.1,
            threshold = 0.3):
    
    env = create_env(number_agents,width,height,n_start_goal,seed)
    total_rewards_by_episode = []
    delta_norms = []

    Q_table = Qtable(env, initial_value, learning_rate, gamma)
    total_time = datetime.now()

    for episode in range(n_episodes):

        index_actions = get_product_set([[0,1,2,3,4]] * number_agents)
        index_actions = dict(zip(index_actions, list(range(len(index_actions)))))

        if episode == 100:        
            Q_old = Q_table.Q.copy()
            Q_old_index = Q_table.dico.copy()               
        elif episode % 100 == 0 and episode>100:              
            delta_norm= get_delta(Q_old, Q_old_index, Q_table.Q.copy(), Q_table.dico.copy())
            delta_norms.append(delta_norm)
            Q_old = Q_table.Q.copy()      
            Q_old_index = Q_table.dico.copy()
        
        if episode > 500 and episode % 100 == 0:
            print(delta_norm)
            print(np.array(delta_norms[-3:]).mean())
            print()
            if np.array(delta_norms[-3:]).mean() < threshold:
                return -(max(total_rewards_by_episode) -1), episode, datetime.now() - total_time     
       
        epsilon = min(1,(np.log(episode + 2) / (episode +1 )) * (number_agents)**4)
        step = 0
        total_reward = 0
        position = get_agent_states(env, start = True) 
        done = False
        np.random.seed()
                
        while step < n_steps:
            
            if choose_at_random(epsilon):
                action_index = np.random.choice(len(Q_table.valid_actions(position)))
                action = Q_table.valid_actions(position)[action_index]
            else:
                action = Q_table.find_max_action(position)
                
            if number_agents == 1:
                action_dict = {0:action}
            else:
                action_dict = dict(zip(range(number_agents),action))
        
            obs, all_rewards, status, _= env.step(action_dict)        
            new_position = get_agent_states(env) 
            step += 1

            reward = 1
            if status['__all__'] == True :
                done = True
            else:
                for key in status.keys():
                    if status[key] == False:                    
                        reward += -1
            
            total_reward += reward
            Q_table.update(position, new_position, action, reward)
            position = new_position
            
        
            if done:
                break
            
        total_rewards_by_episode.append(total_reward)
        
        env = create_env(number_agents,width,height,n_start_goal,seed)
           
        Q_table.env = env
        
    return -(max(total_rewards_by_episode) -1), -1, datetime.now() - total_time
        

#%%
        
number_agents = 1#np.random.randint(1,5)
width = 8#np.random.randint(3,20)
height = 8#np.random.randint(3,20)
n_start_goal = 3
seed = 4

n_episodes = width*height*number_agents*20
n_steps = 2*(width+height)
epsilon = 0.1

initial_value = 0
learning_rate = 0.8
gamma = 0.95
threshold = 0.3

env = create_env(number_agents,width,height,n_start_goal,seed)
env.step(dict(zip(range(number_agents),[2]*number_agents)))
env_renderer = RenderTool(env,agent_render_variant=3)
env_renderer.render_env(show=True, show_predictions=False, show_observations=False)

cost, episodes, total_time = run(number_agents,
                                    width,height,
                                    n_start_goal,
                                    seed,
                                    n_episodes,
                                    n_steps,
                                    threshold= threshold)







