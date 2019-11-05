import numpy as np
from itertools import product

class QTable(): #for double Q learning
    def __init__(self, n_agents, initial_state, initial_value, gamma, lr):
        self.gamma = gamma
        self.learning_rate = lr
        self.initial_value = initial_value
        self.n_agents = n_agents
        self.table = {}
        self.table_1 = {}
        self.table_2 = {}
        
        def get_product_set(iterables):
            if len(iterables) == 1 :
                return iterables[0]
            else:
                return list(product(*iterables))
            
        self.actions = get_product_set([[1,2,3,4]]*n_agents)
        self.add_state(initial_state,self.actions)
        
        
        
    def add_state(self, state, action):
        to_zip = [self.initial_value]*len(action)
        self.table[state] = dict(zip(action, to_zip))
        self.table_1[state] = dict(zip(action, to_zip))
        self.table_2[state] = dict(zip(action, to_zip))
        
    def update_table(self, state, action, state_, reward):
        
        choice = np.random.choice([1,2])
        
        if state_ not in list(self.table.keys()):
            self.add_state(state_, self.actions)
            if choice == 1:
                self.table_1[state][action] += self.learning_rate * \
                                                    ( reward + self.gamma * self.initial_value \
                                                    - self.table_1[state][action]) 
            else:
                self.table_2[state][action] += self.learning_rate * \
                                    ( reward + self.gamma * self.initial_value \
                                    - self.table_2[state][action]) 
        else:
            if choice == 1:
                t1_max_action_for_state_ =  max(self.table_1[state_], key = self.table_1[state_].get)
                self.table_1[state][action] += self.learning_rate * \
                                                    ( reward + self.gamma * self.table_2[state_][t1_max_action_for_state_] \
                                                    - self.table_1[state][action]) 
            else:
                t2_max_action_for_state_ =  max(self.table_2[state_], key = self.table_2[state_].get)
                self.table_2[state][action] += self.learning_rate * \
                                                    ( reward + self.gamma * self.table_1[state_][t2_max_action_for_state_] \
                                                    - self.table_2[state][action]) 

        for action in self.actions:
            self.table[state][action] = .5*(self.table_1[state][action] + self.table_2[state][action])

    def get_max_action(self, state):
        return max(self.table[state], key = self.table[state].get)