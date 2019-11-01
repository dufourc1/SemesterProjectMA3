from lookuptable import LookUpTable
from agent import Agent
from visualization.graphic import draw_square


class LocalEnv():
    def __init__(self, grid, agents):
        self.table = LookUpTable(grid, make_table=True)
        self.agents = [Agent(agent) for agent in agents]
        self.positions = [ agent.position for agent in self.agents ]
    
    def render(self, env_renderer):
    
        rgb_list = [(255,0,0),(172,0,0),(89,0,0),
            (0,255,0),(0,172,0),(0,89,0),
            (0,0,255),(0,0,172),(0,0,89),
            (255,255,0),(255,172,0),(255,89,0),(255,0,255),(255,0,172),(255,0,89),
            (172,255,0),(172,172,0),(172,89,0),(172,0,255),(172,0,172),(172,0,89),
            (89,255,0),(89,172,0),(89,89,0),(89,0,255),(89,0,172),(89,0,89)]

        for handle, agent in enumerate(self.agents):
            draw_square(env_renderer, agent.position, size = 1 / (handle + 1.2), color = rgb_list[handle])
            env_renderer.render_env(show=True, show_predictions=False, show_observations=False)
            
    def __get_agent_new_state(self, agent, action):
        """
        Returns new agent state as if it were the only agent on the grid
        """
        if agent.speed_data['position_fraction'] == 0. and action == 4 :
            return agent.position, agent.direction, 0. 
        else:
            if agent.speed_data['speed'] + agent.speed_data['position_fraction'] >=1:
                new_position, new_direction = self.table.get_new_state(agent.position, agent.direction, action)
                return new_position, new_direction, 0.
            else:
                return agent.position, agent.direction, agent.speed_data['position_fraction'] + agent.speed_data['speed']
            
    
    def show_agents(self):
        for agent in self.agents:
            print(vars(agent))
    
    def restart_agents(self):
        for agent in self.agents:
            agent.restart()
    
    def step(self, action_dict):
        
#        for handle, action in action_dict.items():
            
        for handle, agent in enumerate(self.agents):
            
            if handle in action_dict.keys():
                agent.set_action(action_dict[handle])

            action = agent.speed_data['transition_action_on_cellexit']
            new_position, new_direction, new_position_fraction = self.__get_agent_new_state(agent, action)
            
            if new_position in self.positions[:handle] or new_position in self.positions[handle + 1:]:
                agent.speed_data['position_fraction'] = new_position_fraction
                agent.old_position, agent.old_direction = agent.position, agent.direction
            else:
                agent.old_position, agent.old_direction = agent.position, agent.direction
                agent.position, agent.direction, agent.speed_data['position_fraction'] = new_position, new_direction, new_position_fraction
            
            if agent.position == agent.target:
                agent.status = 'DONE'
            
            self.positions[handle] = agent.position
            
            
            


