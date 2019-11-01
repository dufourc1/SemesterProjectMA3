import numpy as np


class AgentStatic():
    def __init__(self, EnvAgent):
        self.initial_position = EnvAgent.initial_position
        self.position = EnvAgent.position
        self.initial_position = EnvAgent.initial_position
        self.direction = EnvAgent.direction
        self.target = EnvAgent.target 
        self.moving = EnvAgent.moving
        self.speed_data = EnvAgent.speed_data
        self.malfunction_data = EnvAgent.malfunction_data
#                                            READY_TO_DEPART = 0  # not in grid yet (position is None) -> prediction as if it were at initial position
#                                            ACTIVE = 1  # in grid (position is not None), not done -> prediction is remaining path
#                                            DONE = 2  # in grid (position is not None), but done -> prediction is stay at target forever
#                                            DONE_REMOVED = 3  # removed from grid (position is None) -> prediction is None
        self.status = EnvAgent.status
        self.position = EnvAgent.position
        self.handle = EnvAgent.handle
        self.old_direction = EnvAgent.old_direction
        self.old_position = EnvAgent.old_position
        
class Agent():
    def __init__(self, EnvAgent):
        self.agent_static = AgentStatic(EnvAgent)
        self.initial_position = EnvAgent.initial_position
        self.position = EnvAgent.position
        self.initial_position = EnvAgent.initial_position
        self.direction = EnvAgent.direction
        self.target = EnvAgent.target 
        self.moving = EnvAgent.moving
        self.speed_data = EnvAgent.speed_data
        self.malfunction_data = EnvAgent.malfunction_data
#                                            READY_TO_DEPART = 0  # not in grid yet (position is None) -> prediction as if it were at initial position
#                                            ACTIVE = 1  # in grid (position is not None), not done -> prediction is remaining path
#                                            DONE = 2  # in grid (position is not None), but done -> prediction is stay at target forever
#                                            DONE_REMOVED = 3  # removed from grid (position is None) -> prediction is None
        self.status = EnvAgent.status
        self.position = EnvAgent.position
        self.handle = EnvAgent.handle
        self.old_direction = EnvAgent.old_direction
        self.old_position = EnvAgent.old_position
    
    
    def set_action(self, action):
        if self.speed_data['position_fraction'] == 0. :
            self.speed_data['transition_action_on_cellexit'] = action
    
    def restart(self):
        self.__init__(self.agent_static)