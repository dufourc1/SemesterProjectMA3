import numpy as np

# GLOBAL VARIBALES

COORDINATE_OFFSET = {
    0 : (-1,0),
    1 : (0,1),
    2 : (1,0),
    3 : (0,-1)
}



class LookUpTable():
    def __init__(self, grid, make_table = False):
        '''
        dico has cell coordinate as key and first coordinate of table as item.
        table is (cell) * 4 * 4 *  --- ((x,y) * direction * action).
        
        Actions are defined as follows here :
            '1' : make left turn
            '2' : go forward
            '3' : make right turn
            '4' : stop
        We get rid of the action '0' of flatland, but keep the other actions and corresponding numbers 
        for consistency.
        '''
        self.transition_matrix = grid
        self.number_rail_cell = len(self.transition_matrix.nonzero()[0])
#        self.dico = dict(zip([(self.transition_matrix.nonzero()[0][k], self.transition_matrix.nonzero()[1][k]) for k in range(self.number_rail_cell)], range(self.number_rail_cell)))
        if make_table:
            self.table = self.__make_table()
       
        
    def __make_table(self):
        """
        Makes the Lookup table, which a dict of the form key : current state = (position tuple, direction) and has for
        item : dict of the form key : action and item : new state resulting from action. 
        """
        rail_cell_coord = self.transition_matrix.nonzero()
        state_actions_dic = {}
        
        for k in range(self.number_rail_cell):
            
            position = (rail_cell_coord[0][k],rail_cell_coord[1][k])
            all_actions = self.get_all_actions(position, bool_result = False)
            
            for direction, actions in all_actions.items():
                
                if len(actions) > 0:
                    actions_newstates_dic = {}
                    for action in actions:
                    
                        new_position, new_direction = self.get_new_state(position, direction, action)
                        actions_newstates_dic[action] = (new_position, new_direction)
                        
                    state_actions_dic[(position,direction)] = actions_newstates_dic
                    
        return state_actions_dic
    
    
    def _get_all_directions(self, cell_transition, bool_result = True):
        """
        return the possible new directions given a the cell described by the transition_matrix 
        Parameters
        ----------
        cell_transition : int
        
        Returns
        -------
        dict of lists of length 4, with boolean value in each index, where the key is the orientation at current cell
        """
        result = {}
        
        for direction in range(4):
            result[direction] = self._get_directions(cell_transition, direction, bool_result)
        
        return result
        
    
    def get_all_directions(self, position, bool_result = True):
        return self._get_all_directions(self.transition_matrix[position[0],position[1]], bool_result)
    
    
    def _get_directions(self, cell_transition, direction, bool_result = True):
        """
        return the possible new directions given current direction from the cell described by the transition_matrix 
        Parameters
        ----------
        cell_transition : int
        orientation : int (0,1,2,3) <-> (N,E,S,W)
        
        Returns
        -------
        list of length 4, with boolean value in each index if bool_result = True
        or list of possible directions length, with value corresponding to the new directions.
        """
        if bool_result:
            result = list(format(cell_transition >> ((3 - direction) * 4) & 0xF, '04b'))
            return [int(x) for x in result]
        else:
            result = []
            new_directions = format(cell_transition >> ((3 - direction) * 4) & 0xF, '04b')
            for index, char in enumerate(new_directions):
                if char ==  '1':
                    result.append(index)
            return result
        
    
    def get_directions(self, position, direction, bool_result = True):
        return self._get_directions(self.transition_matrix[position[0],position[1]], direction, bool_result)
        
    
    def _get_all_actions(self, cell_transition, bool_result = True):
        """
        Return the possible actions for all directions.
        
        Parameters
        ----------
        cell_transition : int 
        bool_result : bool
        
        Returns
        -------
        dict of 4 lists of size 4 with 1 in indices of possible actions if bool_result, 0 if not possible (key : direction, item : list)
        dict of 4 lists containing the possible actions if bool_result is false. (key : direction, item : list)
        """
        result = {}
        
        for direction in range(4):
            result[direction] = self._get_actions(cell_transition, direction, bool_result)
        
        return result
            
    
    def get_all_actions(self, position, bool_result = True):
        return self._get_all_actions(self.transition_matrix[position[0],position[1]], bool_result )
    
    
    def _get_actions(self, cell_transition, direction, bool_result = True):
        """
        Returns the possible actions that can be taken from given cell in given direction.
        The notion of possible action differs from that of flatland, in the sense that each action returned here
        will return a different new state when taken. (i.e. no action '0')
        
        Actions are defined as follows here :
        '1' : make left turn
        '2' : go forward
        '3' : make right turn
        '4' : stop
        
        Parameters
        ---------
        cell_transition : int 
        direction : int
        bool_result : bool
        
        Returns
        -------
        list of size 4 with 1 in indices of possible actions if bool_result.
        list containing the possible actions otherwise.
        """
        
        new_directions = self._get_directions(cell_transition, direction, bool_result = False)
        
        if len(new_directions) == 1: #when only one new direction exists only go forward is valid
            if bool_result:
                return [0,1,0,0]
            else:
                return [2]
        
        if bool_result:
            result = [0,0,0,0]
            
            for new_direction in new_directions:
                delta = direction - new_direction
                
                if delta == 0 : #go forward
                    result[1] = 1 #allow go forward action
                else:
                    result[delta % 4 -1 ] = 1 # allow right or left turn
            
            return result
        else:
            result = []
            
            for new_direction in new_directions:
                delta = direction - new_direction
                
                if delta == 0: #go forward 
                    result.append(2) #allow go forward action
                else:
                    result.append(delta % 4) # allow right or left turn
            
            return result
        
        
    def get_actions(self, position, direction, bool_result = True):
        return self._get_actions(self.transition_matrix[position[0],position[1]], direction, bool_result)
        
        
    def __is_cell_endpoint(self, cell_transition):
        """
        Checks if the given cell is an endpoint
        """
        all_directions = self._get_all_directions(cell_transition,bool_result=False)
        
        count = 0
        for key, item in all_directions.items():
            if len(item) > 0:
                count +=1
        
        if count != 1:
            return False
        else:
            return True
        
        
    def __offset(self, new_direction):
        """
        returns the coordinate offset from new direction
        Parameters
        ----------
        direction:int
        new_direction:int
        
        Returns
        -------
        tuple size two 
        """
        return COORDINATE_OFFSET[new_direction]
    
    
    def __offset_action(self, position, direction, action):
        """
        returns the coordinate offset from agent state ( = position + direction) under action.
        Parameters
        ----------
        direction : int
        action : int
        
        Returns
        -------
        tuple size two : offset
        int : new direction
        """
        if action == 2:
            possible_new_directions = self.get_directions(position, direction, bool_result = False)
            if len(possible_new_directions) == 1 :
                new_direction = possible_new_directions[0]
            else:
                new_direction = direction
            return self.__offset(new_direction), new_direction# WARNING, THIS DOES NOT DEAL WITH ENDPOINTS
        elif action != 4:
            new_direction = (direction - action) % 4
            return self.__offset(new_direction), new_direction
        else:
            return (0,0), direction
    
    
    def get_new_state(self, position, direction, action):
        """
        returns the coordinates and direction on new cell given an action
        Parameters
        ----------
        position : tuple size 2
        direction : int in range(4)
        action : int in range(4)
        
        Returns
        -------
        tuple, int : new position, new direction
        """
        if not self.__is_cell_endpoint(self.transition_matrix[position[0],position[1]]):
            offset, new_direction = self.__offset_action(position, direction, action)
            return tuple(map(lambda x, y : x+y, position, offset)), new_direction
        else:
            new_direction = (direction + 2) % 4
            offset = self.__offset(new_direction)
            return tuple(map(lambda x, y : x+y, position, offset)), new_direction





