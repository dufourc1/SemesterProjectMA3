import random
import numpy as np
import matplotlib.pyplot as plt
from flatland.envs.observations import TreeObsForRailEnv
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_generators import complex_rail_generator
from flatland.envs.schedule_generators import complex_schedule_generator
from flatland.utils.rendertools import RenderTool
from visualization.graphic import graphic_coordinate,draw_path,draw_multiple_paths
from navigation.navigation_path import actions_for_path,walk_path,walk_many_paths
from utils import get_rail_coordinates
from datetime import datetime


random.seed(1)
np.random.seed(1)



#%%

def choose_at_random(epsilon):
    decision = [0, 1]
    proba = [1-epsilon, epsilon]
    return np.random.choice(decision, p=proba)

def get_agent_state(env):
    return((env.agents[0].position[0],env.agents[0].position[1],env.agents[0].direction))

#%%
class Qtable():
    
    def __init__(self, env, init_val, learning_rate, gamma, n_actions = 5, n_directions = 4):
        self.Q_1 = np.array([[{2 : 0}]])
        self.Q_2 = np.array([[{2 : 0}]])
        self.Q = np.array([[{2 : 0}]])
        self.env = env
        self.n_actions = n_actions
        self.init_v = init_val
        self.lr = learning_rate
        self.y = gamma
        self.dico_1 = {(env.agents[0].position[0],env.agents[0].position[1],env.agents[0].direction) : 0}
        self.dico_2 = {(env.agents[0].position[0],env.agents[0].position[1],env.agents[0].direction) : 0}
        self.dico = {(env.agents[0].position[0],env.agents[0].position[1],env.agents[0].direction) : 0}
    
    def get_next_step(self, state):
        #NESW
        possible_actions = []
        new_states = []

        for action in range(self.n_actions-1):
            cell_free, new_cell_valid, new_direction, new_position, transition_valid = env._check_action_on_agent(action, env.agents[0])
            if transition_valid in [True, 1]:
                possible_actions.append(action)
                new_states.append(tuple(list(new_position) + [new_direction]))
                
        #action 4 is badly handled : bad next position
        possible_actions.append(4)
        new_states.append(state)
        
        return possible_actions, new_states

    def add_row(self, state):
        possible_actions, new_states = self.get_next_step(state)
        action_dict = dict(zip(possible_actions,[self.init_v]*len(possible_actions)))
        self.Q = np.vstack((self.Q, action_dict))
        return len(self.Q)-1        
    
    def add_row_1(self, state):
        possible_actions, new_states = self.get_next_step(state)
        action_dict = dict(zip(possible_actions,[self.init_v]*len(possible_actions)))
        self.Q_1 = np.vstack((self.Q_1, action_dict))
        return len(self.Q_1)-1

    def add_row_2(self, state):
        possible_actions, new_states = self.get_next_step(state)
        action_dict = dict(zip(possible_actions,[self.init_v]*len(possible_actions)))
        self.Q_2 = np.vstack((self.Q_2, action_dict))
        return len(self.Q_2)-1

    def update(self, state, state_, action, reward):

        if state_ not in self.dico.keys():
            self.dico[state_] = self.add_row(state_)       
        if state_ not in self.dico_1.keys():
            self.dico_1[state_] = self.add_row_1(state_)       
        if state_ not in self.dico_2.keys():
            self.dico_2[state_] = self.add_row_2(state_)       
             
#        if state not in self.dico_2.keys():
#            self.dico_2[state] = self.add_row_2()               
#        if state not in self.dico_1.keys():
#            self.dico_1[state] = self.add_row_1(row)
    
        choice = np.random.choice([1,2])
        if choice == 1 :
            Q_1_max_value_action_for_state_ = max(self.Q_1[self.dico_1[state_]][0], key = self.Q_1[self.dico_1[state_]][0].get) 
            self.Q_1[self.dico_1[state]][0][action] += self.lr * (reward + self.y * self.Q_2[self.dico_1[state_]][0][Q_1_max_value_action_for_state_] - self.Q_1[self.dico_1[state]][0][action])
        else:
            Q_2_max_value_action_for_state_ = max(self.Q_2[self.dico_1[state_]][0], key = self.Q_2[self.dico_1[state_]][0].get) 
            self.Q_2[self.dico_1[state]][0][action] += self.lr * (reward + self.y * self.Q_1[self.dico_1[state_]][0][Q_2_max_value_action_for_state_] - self.Q_2[self.dico_1[state]][0][action])
        
        row_Q_1 = self.Q_1[self.dico_1[state]][0]
        row_Q_2 = self.Q_2[self.dico_2[state]][0]
        row_Q = {}
        for key in row_Q_1.keys():
            row_Q[key] = (row_Q_1[key] + row_Q_2[key])/2
        
        self.Q[self.dico[state]][0] = row_Q
        
    def valid_actions(self, state):
        row_Q_1 = self.Q_1[self.dico_1[state]][0]
        return list(row_Q_1.keys())
        
    def find_max_action(self, state):
#        row_Q_1 = self.Q_1[self.dico_1[state]][0]
#        row_Q_2 = self.Q_2[self.dico_2[state]][0]
#        row_sum = {}
        
#        for key in row_Q_1.keys():
#            row_sum[key] = row_Q_1[key] + row_Q_2[key]
        
#        return max(row_sum, row_sum.get)
        return max(self.Q[self.dico[state]][0], key = self.Q[self.dico[state]][0].get )
#%%

number_agents = 1
features_per_node = 9

env = RailEnv(width=7,
              height=7,
              rail_generator=complex_rail_generator(nr_start_goal=10, nr_extra=1, min_dist=8, max_dist=99999, seed=1),
              schedule_generator=complex_schedule_generator(),
              number_of_agents=number_agents,
              obs_builder_object=TreeObsForRailEnv(max_depth=2))

        
n_episodes = 10000
n_steps = 30
epsilon = 0.1


#random.seed(1)
#np.random.seed(1)

start_time = datetime.now()
lap_time = datetime.now()
steps_by_episode = []
total_rewards_by_episode = []

Q_table = Qtable(env, 0, 0.8, 0.9)
x = Q_table.Q
for episode in range(n_episodes):

    if episode % 100 == 0:
            print('episode:', episode)
            print('in', datetime.now() - lap_time)
            lap_time = datetime.now()
    
#    epsilon = 1 / (1+ np.log(episode +1) )
    epsilon = 1 / (episode + 1)
    step = 0
    total_reward = 0
    position = get_agent_state(env)
    done = False
 
    np.random.seed()
    
    while step < n_steps:
        step += 1
        if choose_at_random(epsilon):
            action = np.random.choice(Q_table.valid_actions(position))
        else:
            action = Q_table.find_max_action(position)
        
        obs, all_rewards, status, _= env.step({0:action})        
        new_position = get_agent_state(env) 
        
        if env.agents[0].position == env.agents[0].target:
            reward = 1
            done = True
        else:
            reward = -1
        
        total_reward += reward
        Q_table.update(position, new_position, action, reward)
        position = new_position

        if done:
            break
        
    
    steps_by_episode.append(step)
    total_rewards_by_episode.append(total_reward)
    
    env.restart_agents()
    if done:
        env.dones = {0: False, '__all__': False}


#%%



env = RailEnv(width=7,
              height=7,
              rail_generator=complex_rail_generator(nr_start_goal=10, nr_extra=1, min_dist=8, max_dist=99999, seed=1),
              schedule_generator=complex_schedule_generator(),
              number_of_agents=2,
              obs_builder_object=TreeObsForRailEnv(max_depth=2))
#env.reset()
env_renderer = RenderTool(env,agent_render_variant=3)
env_renderer.render_env(show=True, show_predictions=False, show_observations=False)

#%%
steps_by_episode = np.array(steps_by_episode)
plt.plot(moving_average(steps_by_episode,200))

#%%
#qq = QTable(env, get_rail_coordinates(env),3,3,3)