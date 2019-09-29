"""
Collection of environment-specific ObservationBuilder.
"""
import pprint
from typing import Optional, List, Dict, T, Tuple

import numpy as np

from flatland.core.env import Environment
from flatland.core.env_observation_builder import ObservationBuilder
from flatland.core.env_prediction_builder import PredictionBuilder
from flatland.core.grid.grid4_utils import get_new_position
from flatland.core.grid.grid_utils import coordinate_to_position
from flatland.utils.ordered_set import OrderedSet


class TreeObsForRailEnv(ObservationBuilder):
    """
    TreeObsForRailEnv object.

    This object returns observation vectors for agents in the RailEnv environment.
    The information is local to each agent and exploits the graph structure of the rail
    network to simplify the representation of the state of the environment for each agent.

    For details about the features in the tree observation see the get() function.
    """

    def __init__(self, max_depth: int, predictor: PredictionBuilder = None):
        super().__init__()
        self.max_depth = max_depth
        self.observation_dim = 11
        # Compute the size of the returned observation vector
        size = 0
        pow4 = 1
        for i in range(self.max_depth + 1):
            size += pow4
            pow4 *= 4
        self.observation_space = [size * self.observation_dim]
        self.location_has_agent = {}
        self.location_has_agent_direction = {}
        self.predictor = predictor
        self.location_has_target = None
        self.tree_explored_actions = [1, 2, 3, 0]
        self.tree_explorted_actions_char = ['L', 'F', 'R', 'B']

    def reset(self):
        self.location_has_target = {tuple(agent.target): 1 for agent in self.env.agents}

    def get_many(self, handles: Optional[List[int]] = None) -> Dict[int, List[int]]:
        """
        Called whenever an observation has to be computed for the `env` environment, for each agent with handle
        in the `handles` list.
        """

        if handles is None:
            handles = []
        if self.predictor:
            self.max_prediction_depth = 0
            self.predicted_pos = {}
            self.predicted_dir = {}
            self.predictions = self.predictor.get()
            if self.predictions:

                for t in range(len(self.predictions[0])):
                    pos_list = []
                    dir_list = []
                    for a in handles:
                        pos_list.append(self.predictions[a][t][1:3])
                        dir_list.append(self.predictions[a][t][3])
                    self.predicted_pos.update({t: coordinate_to_position(self.env.width, pos_list)})
                    self.predicted_dir.update({t: dir_list})
                self.max_prediction_depth = len(self.predicted_pos)
        observations = {}
        for h in handles:
            observations[h] = self.get(h)
        return observations

    def get(self, handle: int = 0) -> List[int]:
        """
        Computes the current observation for agent `handle` in env

        The observation vector is composed of 4 sequential parts, corresponding to data from the up to 4 possible
        movements in a RailEnv (up to because only a subset of possible transitions are allowed in RailEnv).
        The possible movements are sorted relative to the current orientation of the agent, rather than NESW as for
        the transitions. The order is::

            [data from 'left'] + [data from 'forward'] + [data from 'right'] + [data from 'back']

        Each branch data is organized as::

            [root node information] +
            [recursive branch data from 'left'] +
            [... from 'forward'] +
            [... from 'right] +
            [... from 'back']

        Each node information is composed of 9 features:

        #1:
            if own target lies on the explored branch the current distance from the agent in number of cells is stored.

        #2:
            if another agents target is detected the distance in number of cells from the agents current location\
            is stored

        #3:
            if another agent is detected the distance in number of cells from current agent position is stored.

        #4:
            possible conflict detected
            tot_dist = Other agent predicts to pass along this cell at the same time as the agent, we store the \
             distance in number of cells from current agent position

            0 = No other agent reserve the same cell at similar time

        #5:
            if an not usable switch (for agent) is detected we store the distance.

        #6:
            This feature stores the distance in number of cells to the next branching  (current node)

        #7:
            minimum distance from node to the agent's target given the direction of the agent if this path is chosen

        #8:
            agent in the same direction
            n = number of agents present same direction \
                (possible future use: number of other agents in the same direction in this branch)
            0 = no agent present same direction

        #9:
            agent in the opposite direction
            n = number of agents present other direction than myself (so conflict) \
                (possible future use: number of other agents in other direction in this branch, ie. number of conflicts)
            0 = no agent present other direction than myself

        #10:
            malfunctioning/blokcing agents
            n = number of time steps the oberved agent remains blocked

        #11:
            slowest observed speed of an agent in same direction
            1 if no agent is observed

            min_fractional speed otherwise

        Missing/padding nodes are filled in with -inf (truncated).
        Missing values in present node are filled in with +inf (truncated).


        In case of the root node, the values are [0, 0, 0, 0, distance from agent to target, own malfunction, own speed]
        In case the target node is reached, the values are [0, 0, 0, 0, 0].
        """

        # Update local lookup table for all agents' positions
        self.location_has_agent = {tuple(agent.position): 1 for agent in self.env.agents}
        self.location_has_agent_direction = {tuple(agent.position): agent.direction for agent in self.env.agents}
        self.location_has_agent_speed = {tuple(agent.position): agent.speed_data['speed'] for agent in self.env.agents}
        self.location_has_agent_malfunction = {tuple(agent.position): agent.malfunction_data['malfunction'] for agent in
                                               self.env.agents}

        if handle > len(self.env.agents):
            print("ERROR: obs _get - handle ", handle, " len(agents)", len(self.env.agents))
        agent = self.env.agents[handle]  # TODO: handle being treated as index
        possible_transitions = self.env.rail.get_transitions(*agent.position, agent.direction)
        num_transitions = np.count_nonzero(possible_transitions)

        # Root node - current position
        # Here information about the agent itself is stored
        distance_map = self.env.distance_map.get()
        observation = [0, 0, 0, 0, 0, 0, distance_map[(handle, *agent.position, agent.direction)], 0, 0,
                       agent.malfunction_data['malfunction'], agent.speed_data['speed']]

        visited = OrderedSet()

        # Start from the current orientation, and see which transitions are available;
        # organize them as [left, forward, right, back], relative to the current orientation
        # If only one transition is possible, the tree is oriented with this transition as the forward branch.
        orientation = agent.direction

        if num_transitions == 1:
            orientation = np.argmax(possible_transitions)

        for branch_direction in [(orientation + i) % 4 for i in range(-1, 3)]:
            if possible_transitions[branch_direction]:
                new_cell = get_new_position(agent.position, branch_direction)
                branch_observation, branch_visited = \
                    self._explore_branch(handle, new_cell, branch_direction, 1, 1)
                observation = observation + branch_observation
                visited |= branch_visited
            else:
                # add cells filled with infinity if no transition is possible
                observation = observation + [-np.inf] * self._num_cells_to_fill_in(self.max_depth)
        self.env.dev_obs_dict[handle] = visited

        return observation

    def _num_cells_to_fill_in(self, remaining_depth):
        """Computes the length of observation vector: sum_{i=0,depth-1} 2^i * observation_dim."""
        num_observations = 0
        pow4 = 1
        for i in range(remaining_depth):
            num_observations += pow4
            pow4 *= 4
        return num_observations * self.observation_dim

    def _explore_branch(self, handle, position, direction, tot_dist, depth):
        """
        Utility function to compute tree-based observations.
        We walk along the branch and collect the information documented in the get() function.
        If there is a branching point a new node is created and each possible branch is explored.
        """

        # [Recursive branch opened]
        if depth >= self.max_depth + 1:
            return [], []

        # Continue along direction until next switch or
        # until no transitions are possible along the current direction (i.e., dead-ends)
        # We treat dead-ends as nodes, instead of going back, to avoid loops
        exploring = True
        last_is_switch = False
        last_is_dead_end = False
        last_is_terminal = False  # wrong cell OR cycle;  either way, we don't want the agent to land here
        last_is_target = False

        visited = OrderedSet()
        agent = self.env.agents[handle]
        time_per_cell = np.reciprocal(agent.speed_data["speed"])
        own_target_encountered = np.inf
        other_agent_encountered = np.inf
        other_target_encountered = np.inf
        potential_conflict = np.inf
        unusable_switch = np.inf
        other_agent_same_direction = 0
        other_agent_opposite_direction = 0
        malfunctioning_agent = 0
        min_fractional_speed = 1.
        num_steps = 1
        while exploring:
            # #############################
            # #############################
            # Modify here to compute any useful data required to build the end node's features. This code is called
            # for each cell visited between the previous branching node and the next switch / target / dead-end.
            if position in self.location_has_agent:
                if tot_dist < other_agent_encountered:
                    other_agent_encountered = tot_dist

                # Check if any of the observed agents is malfunctioning, store agent with longest duration left
                if self.location_has_agent_malfunction[position] > malfunctioning_agent:
                    malfunctioning_agent = self.location_has_agent_malfunction[position]

                if self.location_has_agent_direction[position] == direction:
                    # Cummulate the number of agents on branch with same direction
                    other_agent_same_direction += 1

                    # Check fractional speed of agents
                    current_fractional_speed = self.location_has_agent_speed[position]
                    if current_fractional_speed < min_fractional_speed:
                        min_fractional_speed = current_fractional_speed

                if self.location_has_agent_direction[position] != direction:
                    # Cummulate the number of agents on branch with other direction
                    other_agent_opposite_direction += 1

            # Check number of possible transitions for agent and total number of transitions in cell (type)
            cell_transitions = self.env.rail.get_transitions(*position, direction)
            transition_bit = bin(self.env.rail.get_full_transitions(*position))
            total_transitions = transition_bit.count("1")
            crossing_found = False
            if int(transition_bit, 2) == int('1000010000100001', 2):
                crossing_found = True

            # Register possible future conflict
            predicted_time = int(tot_dist * time_per_cell)
            if self.predictor and predicted_time < self.max_prediction_depth:
                int_position = coordinate_to_position(self.env.width, [position])
                if tot_dist < self.max_prediction_depth:

                    pre_step = max(0, predicted_time - 1)
                    post_step = min(self.max_prediction_depth - 1, predicted_time + 1)

                    # Look for conflicting paths at distance tot_dist
                    if int_position in np.delete(self.predicted_pos[predicted_time], handle, 0):
                        conflicting_agent = np.where(self.predicted_pos[predicted_time] == int_position)
                        for ca in conflicting_agent[0]:
                            if direction != self.predicted_dir[predicted_time][ca] and cell_transitions[
                                self._reverse_dir(
                                    self.predicted_dir[predicted_time][ca])] == 1 and tot_dist < potential_conflict:
                                potential_conflict = tot_dist
                            if self.env.dones[ca] and tot_dist < potential_conflict:
                                potential_conflict = tot_dist

                    # Look for conflicting paths at distance num_step-1
                    elif int_position in np.delete(self.predicted_pos[pre_step], handle, 0):
                        conflicting_agent = np.where(self.predicted_pos[pre_step] == int_position)
                        for ca in conflicting_agent[0]:
                            if direction != self.predicted_dir[pre_step][ca] \
                                and cell_transitions[self._reverse_dir(self.predicted_dir[pre_step][ca])] == 1 \
                                and tot_dist < potential_conflict:  # noqa: E125
                                potential_conflict = tot_dist
                            if self.env.dones[ca] and tot_dist < potential_conflict:
                                potential_conflict = tot_dist

                    # Look for conflicting paths at distance num_step+1
                    elif int_position in np.delete(self.predicted_pos[post_step], handle, 0):
                        conflicting_agent = np.where(self.predicted_pos[post_step] == int_position)
                        for ca in conflicting_agent[0]:
                            if direction != self.predicted_dir[post_step][ca] and cell_transitions[self._reverse_dir(
                                self.predicted_dir[post_step][ca])] == 1 \
                                and tot_dist < potential_conflict:  # noqa: E125
                                potential_conflict = tot_dist
                            if self.env.dones[ca] and tot_dist < potential_conflict:
                                potential_conflict = tot_dist

            if position in self.location_has_target and position != agent.target:
                if tot_dist < other_target_encountered:
                    other_target_encountered = tot_dist

            if position == agent.target and tot_dist < own_target_encountered:
                own_target_encountered = tot_dist

            # #############################
            # #############################
            if (position[0], position[1], direction) in visited:
                last_is_terminal = True
                break
            visited.add((position[0], position[1], direction))

            # If the target node is encountered, pick that as node. Also, no further branching is possible.
            if np.array_equal(position, self.env.agents[handle].target):
                last_is_target = True
                break

            # Check if crossing is found --> Not an unusable switch
            if crossing_found:
                # Treat the crossing as a straight rail cell
                total_transitions = 2
            num_transitions = np.count_nonzero(cell_transitions)

            exploring = False

            # Detect Switches that can only be used by other agents.
            if total_transitions > 2 > num_transitions and tot_dist < unusable_switch:
                unusable_switch = tot_dist

            if num_transitions == 1:
                # Check if dead-end, or if we can go forward along direction
                nbits = total_transitions
                if nbits == 1:
                    # Dead-end!
                    last_is_dead_end = True

                if not last_is_dead_end:
                    # Keep walking through the tree along `direction`
                    exploring = True
                    # convert one-hot encoding to 0,1,2,3
                    direction = np.argmax(cell_transitions)
                    position = get_new_position(position, direction)
                    num_steps += 1
                    tot_dist += 1
            elif num_transitions > 0:
                # Switch detected
                last_is_switch = True
                break

            elif num_transitions == 0:
                # Wrong cell type, but let's cover it and treat it as a dead-end, just in case
                print("WRONG CELL TYPE detected in tree-search (0 transitions possible) at cell", position[0],
                      position[1], direction)
                last_is_terminal = True
                break

        # `position` is either a terminal node or a switch

        # #############################
        # #############################
        # Modify here to append new / different features for each visited cell!

        if last_is_target:
            observation = [own_target_encountered,
                           other_target_encountered,
                           other_agent_encountered,
                           potential_conflict,
                           unusable_switch,
                           tot_dist,
                           0,
                           other_agent_same_direction,
                           other_agent_opposite_direction,
                           malfunctioning_agent,
                           min_fractional_speed
                           ]

        elif last_is_terminal:
            observation = [own_target_encountered,
                           other_target_encountered,
                           other_agent_encountered,
                           potential_conflict,
                           unusable_switch,
                           np.inf,
                           self.env.distance_map.get()[handle, position[0], position[1], direction],
                           other_agent_same_direction,
                           other_agent_opposite_direction,
                           malfunctioning_agent,
                           min_fractional_speed
                           ]

        else:
            observation = [own_target_encountered,
                           other_target_encountered,
                           other_agent_encountered,
                           potential_conflict,
                           unusable_switch,
                           tot_dist,
                           self.env.distance_map.get()[handle, position[0], position[1], direction],
                           other_agent_same_direction,
                           other_agent_opposite_direction,
                           malfunctioning_agent,
                           min_fractional_speed
                           ]
        # #############################
        # #############################
        # Start from the current orientation, and see which transitions are available;
        # organize them as [left, forward, right, back], relative to the current orientation
        # Get the possible transitions
        possible_transitions = self.env.rail.get_transitions(*position, direction)
        for branch_direction in [(direction + 4 + i) % 4 for i in range(-1, 3)]:
            if last_is_dead_end and self.env.rail.get_transition((*position, direction),
                                                                 (branch_direction + 2) % 4):
                # Swap forward and back in case of dead-end, so that an agent can learn that going forward takes
                # it back
                new_cell = get_new_position(position, (branch_direction + 2) % 4)
                branch_observation, branch_visited = self._explore_branch(handle,
                                                                          new_cell,
                                                                          (branch_direction + 2) % 4,
                                                                          tot_dist + 1,
                                                                          depth + 1)
                observation = observation + branch_observation
                if len(branch_visited) != 0:
                    visited |= branch_visited
            elif last_is_switch and possible_transitions[branch_direction]:
                new_cell = get_new_position(position, branch_direction)
                branch_observation, branch_visited = self._explore_branch(handle,
                                                                          new_cell,
                                                                          branch_direction,
                                                                          tot_dist + 1,
                                                                          depth + 1)
                observation = observation + branch_observation
                if len(branch_visited) != 0:
                    visited |= branch_visited
            else:
                # no exploring possible, add just cells with infinity
                observation = observation + [-np.inf] * self._num_cells_to_fill_in(self.max_depth - depth)

        return observation, visited

    def util_print_obs_subtree(self, tree):
        """
        Utility function to pretty-print tree observations returned by this object.
        """
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(self.unfold_observation_tree(tree))

    def unfold_observation_tree(self, tree, current_depth=0, actions_for_display=True):
        """
        Utility function to pretty-print tree observations returned by this object.
        """
        if len(tree) < self.observation_dim:
            return

        depth = 0
        tmp = len(tree) / self.observation_dim - 1
        pow4 = 4
        while tmp > 0:
            tmp -= pow4
            depth += 1
            pow4 *= 4

        unfolded = {}
        unfolded[''] = tree[0:self.observation_dim]
        child_size = (len(tree) - self.observation_dim) // 4
        for child in range(4):
            child_tree = tree[(self.observation_dim + child * child_size):
                              (self.observation_dim + (child + 1) * child_size)]
            observation_tree = self.unfold_observation_tree(child_tree, current_depth=current_depth + 1)
            if observation_tree is not None:
                if actions_for_display:
                    label = self.tree_explorted_actions_char[child]
                else:
                    label = self.tree_explored_actions[child]
                unfolded[label] = observation_tree
        return unfolded

    def set_env(self, env: Environment):
        super().set_env(env)
        if self.predictor:
            self.predictor.set_env(self.env)

    def _reverse_dir(self, direction):
        return int((direction + 2) % 4)


class GlobalObsForRailEnv(ObservationBuilder):
    """
    Gives a global observation of the entire rail environment.
    The observation is composed of the following elements:

        - transition map array with dimensions (env.height, env.width, 16),\
          assuming 16 bits encoding of transitions.

        - Two 2D arrays (map_height, map_width, 2) containing respectively the position of the given agent\
         target and the positions of the other agents targets.

        - A 3D array (map_height, map_width, 4) wtih
            - first channel containing the agents position and direction
            - second channel containing the other agents positions and diretions
            - third channel containing agent malfunctions
            - fourth channel containing agent fractional speeds
    """

    def __init__(self):
        self.observation_space = ()
        super(GlobalObsForRailEnv, self).__init__()

    def set_env(self, env: Environment):
        super().set_env(env)
        self.observation_space = [4, self.env.height, self.env.width]

    def reset(self):
        self.rail_obs = np.zeros((self.env.height, self.env.width, 16))
        for i in range(self.rail_obs.shape[0]):
            for j in range(self.rail_obs.shape[1]):
                bitlist = [int(digit) for digit in bin(self.env.rail.get_full_transitions(i, j))[2:]]
                bitlist = [0] * (16 - len(bitlist)) + bitlist
                self.rail_obs[i, j] = np.array(bitlist)

    def get(self, handle: int = 0) -> (np.ndarray, np.ndarray, np.ndarray):
        obs_targets = np.zeros((self.env.height, self.env.width, 2))
        obs_agents_state = np.zeros((self.env.height, self.env.width, 4))
        agents = self.env.agents
        agent = agents[handle]

        agent_pos = agents[handle].position
        obs_agents_state[agent_pos][0] = agents[handle].direction
        obs_targets[agent.target][0] = 1

        for i in range(len(agents)):
            if i != handle:  # TODO: handle used as index...?
                agent2 = agents[i]
                obs_agents_state[agent2.position][1] = agent2.direction
                obs_targets[agent2.target][1] = 1
            obs_agents_state[agents[i].position][2] = agents[i].malfunction_data['malfunction']
            obs_agents_state[agents[i].position][3] = agents[i].speed_data['speed']

        return self.rail_obs, obs_agents_state, obs_targets


class LocalObsForRailEnv(ObservationBuilder):
    """
    !!!!!!WARNING!!! THIS IS DEPRACTED AND NOT UPDATED TO FLATLAND 2.0!!!!!
    Gives a local observation of the rail environment around the agent.
    The observation is composed of the following elements:

        - transition map array of the local environment around the given agent, \
          with dimensions (view_height,2*view_width+1, 16), \
          assuming 16 bits encoding of transitions.

        - Two 2D arrays (view_height,2*view_width+1, 2) containing respectively, \
        if they are in the agent's vision range, its target position, the positions of the other targets.

        - A 2D array (view_height,2*view_width+1, 4) containing the one hot encoding of directions \
          of the other agents at their position coordinates, if they are in the agent's vision range.

        - A 4 elements array with one hot encoding of the direction.

    Use the parameters view_width and view_height to define the rectangular view of the agent.
    The center parameters moves the agent along the height axis of this rectangle. If it is 0 the agent only has
    observation in front of it.

    .. deprecated:: 2.0.0
    """

    def __init__(self, view_width, view_height, center):

        super(LocalObsForRailEnv, self).__init__()
        self.view_width = view_width
        self.view_height = view_height
        self.center = center
        self.max_padding = max(self.view_width, self.view_height - self.center)

    def reset(self):
        # We build the transition map with a view_radius empty cells expansion on each side.
        # This helps to collect the local transition map view when the agent is close to a border.
        self.max_padding = max(self.view_width, self.view_height)
        self.rail_obs = np.zeros((self.env.height,
                                  self.env.width, 16))
        for i in range(self.env.height):
            for j in range(self.env.width):
                bitlist = [int(digit) for digit in bin(self.env.rail.get_full_transitions(i, j))[2:]]
                bitlist = [0] * (16 - len(bitlist)) + bitlist
                self.rail_obs[i, j] = np.array(bitlist)

    def get(self, handle: int = 0) -> (np.ndarray, np.ndarray, np.ndarray, np.ndarray):
        agents = self.env.agents
        agent = agents[handle]

        # Correct agents position for padding
        # agent_rel_pos[0] = agent.position[0] + self.max_padding
        # agent_rel_pos[1] = agent.position[1] + self.max_padding

        # Collect visible cells as set to be plotted
        visited, rel_coords = self.field_of_view(agent.position, agent.direction, )
        local_rail_obs = None

        # Add the visible cells to the observed cells
        self.env.dev_obs_dict[handle] = set(visited)

        # Locate observed agents and their coresponding targets
        local_rail_obs = np.zeros((self.view_height, 2 * self.view_width + 1, 16))
        obs_map_state = np.zeros((self.view_height, 2 * self.view_width + 1, 2))
        obs_other_agents_state = np.zeros((self.view_height, 2 * self.view_width + 1, 4))
        _idx = 0
        for pos in visited:
            curr_rel_coord = rel_coords[_idx]
            local_rail_obs[curr_rel_coord[0], curr_rel_coord[1], :] = self.rail_obs[pos[0], pos[1], :]
            if pos == agent.target:
                obs_map_state[curr_rel_coord[0], curr_rel_coord[1], 0] = 1
            else:
                for tmp_agent in agents:
                    if pos == tmp_agent.target:
                        obs_map_state[curr_rel_coord[0], curr_rel_coord[1], 1] = 1
            if pos != agent.position:
                for tmp_agent in agents:
                    if pos == tmp_agent.position:
                        obs_other_agents_state[curr_rel_coord[0], curr_rel_coord[1], :] = np.identity(4)[
                            tmp_agent.direction]

            _idx += 1

        direction = np.identity(4)[agent.direction]
        return local_rail_obs, obs_map_state, obs_other_agents_state, direction

    def get_many(self, handles: Optional[List[int]] = None) -> Dict[int, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """
        Called whenever an observation has to be computed for the `env` environment, for each agent with handle
        in the `handles` list.
        """

        observations = {}
        if handles is None:
            handles = []
        for h in handles:
            observations[h] = self.get(h)
        return observations

    def field_of_view(self, position, direction, state=None):
        # Compute the local field of view for an agent in the environment
        data_collection = False
        if state is not None:
            temp_visible_data = np.zeros(shape=(self.view_height, 2 * self.view_width + 1, 16))
            data_collection = True
        if direction == 0:
            origin = (position[0] + self.center, position[1] - self.view_width)
        elif direction == 1:
            origin = (position[0] - self.view_width, position[1] - self.center)
        elif direction == 2:
            origin = (position[0] - self.center, position[1] + self.view_width)
        else:
            origin = (position[0] + self.view_width, position[1] + self.center)
        visible = list()
        rel_coords = list()
        for h in range(self.view_height):
            for w in range(2 * self.view_width + 1):
                if direction == 0:
                    if 0 <= origin[0] - h < self.env.height and 0 <= origin[1] + w < self.env.width:
                        visible.append((origin[0] - h, origin[1] + w))
                        rel_coords.append((h, w))
                    # if data_collection:
                    #    temp_visible_data[h, w, :] = state[origin[0] - h, origin[1] + w, :]
                elif direction == 1:
                    if 0 <= origin[0] + w < self.env.height and 0 <= origin[1] + h < self.env.width:
                        visible.append((origin[0] + w, origin[1] + h))
                        rel_coords.append((h, w))
                    # if data_collection:
                    #    temp_visible_data[h, w, :] = state[origin[0] + w, origin[1] + h, :]
                elif direction == 2:
                    if 0 <= origin[0] + h < self.env.height and 0 <= origin[1] - w < self.env.width:
                        visible.append((origin[0] + h, origin[1] - w))
                        rel_coords.append((h, w))
                    # if data_collection:
                    #    temp_visible_data[h, w, :] = state[origin[0] + h, origin[1] - w, :]
                else:
                    if 0 <= origin[0] - w < self.env.height and 0 <= origin[1] - h < self.env.width:
                        visible.append((origin[0] - w, origin[1] - h))
                        rel_coords.append((h, w))
                    # if data_collection:
                    #    temp_visible_data[h, w, :] = state[origin[0] - w, origin[1] - h, :]
        if data_collection:
            return temp_visible_data
        else:
            return visible, rel_coords
