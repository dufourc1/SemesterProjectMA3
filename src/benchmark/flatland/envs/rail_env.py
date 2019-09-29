"""
Definition of the RailEnv environment.
"""
# TODO:  _ this is a global method --> utils or remove later
import warnings
from enum import IntEnum
from typing import List, Set, NamedTuple, Optional, Tuple, Dict

import msgpack
import msgpack_numpy as m
import numpy as np

from flatland.core.env import Environment
from flatland.core.env_observation_builder import ObservationBuilder
from flatland.core.grid.grid4 import Grid4TransitionsEnum
from flatland.core.grid.grid4_utils import get_new_position
from flatland.core.transition_map import GridTransitionMap
from flatland.envs.agent_utils import EnvAgentStatic, EnvAgent
from flatland.envs.distance_map import DistanceMap
from flatland.envs.observations import TreeObsForRailEnv
from flatland.envs.rail_generators import random_rail_generator, RailGenerator
from flatland.envs.schedule_generators import random_schedule_generator, ScheduleGenerator
from flatland.utils.ordered_set import OrderedSet

m.patch()


class RailEnvActions(IntEnum):
    DO_NOTHING = 0  # implies change of direction in a dead-end!
    MOVE_LEFT = 1
    MOVE_FORWARD = 2
    MOVE_RIGHT = 3
    STOP_MOVING = 4

    @staticmethod
    def to_char(a: int):
        return {
            0: 'B',
            1: 'L',
            2: 'F',
            3: 'R',
            4: 'S',
        }[a]


RailEnvGridPos = NamedTuple('RailEnvGridPos', [('r', int), ('c', int)])
RailEnvNextAction = NamedTuple('RailEnvNextAction', [('action', RailEnvActions), ('next_position', RailEnvGridPos),
                                                     ('next_direction', Grid4TransitionsEnum)])


class RailEnv(Environment):
    """
    RailEnv environment class.

    RailEnv is an environment inspired by a (simplified version of) a rail
    network, in which agents (trains) have to navigate to their target
    locations in the shortest time possible, while at the same time cooperating
    to avoid bottlenecks.

    The valid actions in the environment are:

     -   0: do nothing (continue moving or stay still)
     -   1: turn left at switch and move to the next cell; if the agent was not moving, movement is started
     -   2: move to the next cell in front of the agent; if the agent was not moving, movement is started
     -   3: turn right at switch and move to the next cell; if the agent was not moving, movement is started
     -   4: stop moving

    Moving forward in a dead-end cell makes the agent turn 180 degrees and step
    to the cell it came from.


    The actions of the agents are executed in order of their handle to prevent
    deadlocks and to allow them to learn relative priorities.

    Reward Function:

    It costs each agent a step_penalty for every time-step taken in the environment. Independent of the movement
    of the agent. Currently all other penalties such as penalty for stopping, starting and invalid actions are set to 0.

    alpha = 1
    beta = 1
    Reward function parameters:

    - invalid_action_penalty = 0
    - step_penalty = -alpha
    - global_reward = beta
    - stop_penalty = 0  # penalty for stopping a moving agent
    - start_penalty = 0  # penalty for starting a stopped agent

    Stochastic malfunctioning of trains:
    Trains in RailEnv can malfunction if they are halted too often (either by their own choice or because an invalid
    action or cell is selected.

    Every time an agent stops, an agent has a certain probability of malfunctioning. Malfunctions of trains follow a
    poisson process with a certain rate. Not all trains will be affected by malfunctions during episodes to keep
    complexity managable.

    TODO: currently, the parameters that control the stochasticity of the environment are hard-coded in init().
    For Round 2, they will be passed to the constructor as arguments, to allow for more flexibility.

    """
    alpha = 1.0
    beta = 1.0
    # Epsilon to avoid rounding errors
    epsilon = 0.01
    invalid_action_penalty = 0  # previously -2; GIACOMO: we decided that invalid actions will carry no penalty
    step_penalty = -1 * alpha
    global_reward = 1 * beta
    stop_penalty = 0  # penalty for stopping a moving agent
    start_penalty = 0  # penalty for starting a stopped agent

    def __init__(self,
                 width,
                 height,
                 rail_generator: RailGenerator = random_rail_generator(),
                 schedule_generator: ScheduleGenerator = random_schedule_generator(),
                 number_of_agents=1,
                 obs_builder_object: ObservationBuilder = TreeObsForRailEnv(max_depth=2),
                 max_episode_steps=None,
                 stochastic_data=None
                 ):
        """
        Environment init.

        Parameters
        ----------
        rail_generator : function
            The rail_generator function is a function that takes the width,
            height and agents handles of a  rail environment, along with the number of times
            the env has been reset, and returns a GridTransitionMap object and a list of
            starting positions, targets, and initial orientations for agent handle.
            The rail_generator can pass a distance map in the hints or information for specific schedule_generators.
            Implementations can be found in flatland/envs/rail_generators.py
        schedule_generator : function
            The schedule_generator function is a function that takes the grid, the number of agents and optional hints
            and returns a list of starting positions, targets, initial orientations and speed for all agent handles.
            Implementations can be found in flatland/envs/schedule_generators.py
        width : int
            The width of the rail map. Potentially in the future,
            a range of widths to sample from.
        height : int
            The height of the rail map. Potentially in the future,
            a range of heights to sample from.
        number_of_agents : int
            Number of agents to spawn on the map. Potentially in the future,
            a range of number of agents to sample from.
        obs_builder_object: ObservationBuilder object
            ObservationBuilder-derived object that takes builds observation
            vectors for each agent.
        max_episode_steps : int or None
        """
        super().__init__()

        self.rail_generator: RailGenerator = rail_generator
        self.schedule_generator: ScheduleGenerator = schedule_generator
        self.rail_generator = rail_generator
        self.rail: Optional[GridTransitionMap] = None
        self.width = width
        self.height = height

        self.rewards = [0] * number_of_agents
        self.done = False
        self.obs_builder = obs_builder_object
        self.obs_builder._set_env(self)

        self._max_episode_steps = max_episode_steps
        self._elapsed_steps = 0

        self.dones = dict.fromkeys(list(range(number_of_agents)) + ["__all__"], False)

        self.obs_dict = {}
        self.rewards_dict = {}
        self.dev_obs_dict = {}
        self.dev_pred_dict = {}

        self.agents: List[EnvAgent] = [None] * number_of_agents  # live agents
        self.agents_static: List[EnvAgentStatic] = [None] * number_of_agents  # static agent information
        self.num_resets = 0
        self.distance_map = DistanceMap(self.agents, self.height, self.width)

        self.action_space = [1]
        self.observation_space = self.obs_builder.observation_space  # updated on resets?

        # Stochastic train malfunctioning parameters
        if stochastic_data is not None:
            prop_malfunction = stochastic_data['prop_malfunction']
            mean_malfunction_rate = stochastic_data['malfunction_rate']
            malfunction_min_duration = stochastic_data['min_duration']
            malfunction_max_duration = stochastic_data['max_duration']
        else:
            prop_malfunction = 0.
            mean_malfunction_rate = 0.
            malfunction_min_duration = 0.
            malfunction_max_duration = 0.

        # percentage of malfunctioning trains
        self.proportion_malfunctioning_trains = prop_malfunction

        # Mean malfunction in number of stops
        self.mean_malfunction_rate = mean_malfunction_rate

        # Uniform distribution parameters for malfunction duration
        self.min_number_of_steps_broken = malfunction_min_duration
        self.max_number_of_steps_broken = malfunction_max_duration

        # Rest environment
        self.reset()
        self.num_resets = 0  # yes, set it to zero again!

        self.valid_positions = None

    # no more agent_handles
    def get_agent_handles(self):
        return range(self.get_num_agents())

    def get_num_agents(self, static=True):
        if static:
            return len(self.agents_static)
        else:
            return len(self.agents)

    def add_agent_static(self, agent_static):
        """ Add static info for a single agent.
            Returns the index of the new agent.
        """
        self.agents_static.append(agent_static)
        return len(self.agents_static) - 1

    def restart_agents(self):
        """ Reset the agents to their starting positions defined in agents_static
        """
        self.agents = EnvAgent.list_from_static(self.agents_static)

    def reset(self, regen_rail=True, replace_agents=True):
        """ if regen_rail then regenerate the rails.
            if replace_agents then regenerate the agents static.
            Relies on the rail_generator returning agent_static lists (pos, dir, target)
        """

        # TODO https://gitlab.aicrowd.com/flatland/flatland/issues/172
        #  can we not put 'self.rail_generator(..)' into 'if regen_rail or self.rail is None' condition?
        rail, optionals = self.rail_generator(self.width, self.height, self.get_num_agents(), self.num_resets)

        if optionals and 'distance_map' in optionals:
            self.distance_map.set(optionals['distance_map'])

        if regen_rail or self.rail is None:
            self.rail = rail
            self.height, self.width = self.rail.grid.shape
            for r in range(self.height):
                for c in range(self.width):
                    rc_pos = (r, c)
                    check = self.rail.cell_neighbours_valid(rc_pos, True)
                    if not check:
                        warnings.warn("Invalid grid at {} -> {}".format(rc_pos, check))

        if replace_agents:
            agents_hints = None
            if optionals and 'agents_hints' in optionals:
                agents_hints = optionals['agents_hints']

            # TODO https://gitlab.aicrowd.com/flatland/flatland/issues/185
            #  why do we need static agents? could we it more elegantly?
            self.agents_static = EnvAgentStatic.from_lists(
                *self.schedule_generator(self.rail, self.get_num_agents(), agents_hints))
        self.restart_agents()

        for i_agent in range(self.get_num_agents()):
            agent = self.agents[i_agent]

            # A proportion of agent in the environment will receive a positive malfunction rate
            if np.random.random() < self.proportion_malfunctioning_trains:
                agent.malfunction_data['malfunction_rate'] = self.mean_malfunction_rate

            agent.malfunction_data['malfunction'] = 0

            initial_malfunction = self._agent_malfunction(i_agent)

            if initial_malfunction:
                agent.speed_data['transition_action_on_cellexit'] = RailEnvActions.DO_NOTHING

        self.num_resets += 1
        self._elapsed_steps = 0

        # TODO perhaps dones should be part of each agent.
        self.dones = dict.fromkeys(list(range(self.get_num_agents())) + ["__all__"], False)

        # Reset the state of the observation builder with the new environment
        self.obs_builder.reset()
        self.observation_space = self.obs_builder.observation_space  # <-- change on reset?
        self.distance_map.reset(self.agents, self.rail)

        # Return the new observation vectors for each agent
        return self._get_observations()

    def _agent_malfunction(self, i_agent) -> bool:
        """
        Returns true if the agent enters into malfunction. (False, if not broken down or already broken down before).
        """
        agent = self.agents[i_agent]

        # Decrease counter for next event
        if agent.malfunction_data['malfunction_rate'] > 0:
            agent.malfunction_data['next_malfunction'] -= 1

        # Only agents that have a positive rate for malfunctions and are not currently broken are considered
        # If counter has come to zero --> Agent has malfunction
        # set next malfunction time and duration of current malfunction
        if agent.malfunction_data['malfunction_rate'] > 0 >= agent.malfunction_data['malfunction'] and \
            agent.malfunction_data['next_malfunction'] <= 0:
            # Increase number of malfunctions
            agent.malfunction_data['nr_malfunctions'] += 1

            # Next malfunction in number of stops
            next_breakdown = int(
                np.random.exponential(scale=agent.malfunction_data['malfunction_rate']))
            agent.malfunction_data['next_malfunction'] = next_breakdown

            # Duration of current malfunction
            num_broken_steps = np.random.randint(self.min_number_of_steps_broken,
                                                 self.max_number_of_steps_broken + 1) + 1
            agent.malfunction_data['malfunction'] = num_broken_steps
            agent.malfunction_data['moving_before_malfunction'] = agent.moving

            return True
        else:
            # The train was broken before...
            if agent.malfunction_data['malfunction'] > 0:

                # Last step of malfunction --> Agent starts moving again after getting fixed
                if agent.malfunction_data['malfunction'] < 2:
                    agent.malfunction_data['malfunction'] -= 1

                    # restore moving state before malfunction without further penalty
                    self.agents[i_agent].moving = agent.malfunction_data['moving_before_malfunction']

                else:
                    agent.malfunction_data['malfunction'] -= 1

                    # Nothing left to do with broken agent
                    return True
        return False

    def step(self, action_dict_: Dict[int, RailEnvActions]):
        self._elapsed_steps += 1

        # Reset the step rewards
        self.rewards_dict = dict()
        for i_agent in range(self.get_num_agents()):
            self.rewards_dict[i_agent] = 0

        # If we're done, set reward and info_dict and step() is done.
        if self.dones["__all__"]:
            self.rewards_dict = {i: self.global_reward for i in range(self.get_num_agents())}
            info_dict = {
                'action_required': {i: False for i in range(self.get_num_agents())},
                'malfunction': {i: 0 for i in range(self.get_num_agents())},
                'speed': {i: 0 for i in range(self.get_num_agents())}
            }
            return self._get_observations(), self.rewards_dict, self.dones, info_dict

        # Perform step on all agents
        for i_agent in range(self.get_num_agents()):
            self._step_agent(i_agent, action_dict_.get(i_agent))

        # Check for end of episode + set global reward to all rewards!
        if np.all([np.array_equal(agent.position, agent.target) for agent in self.agents]):
            self.dones["__all__"] = True
            self.rewards_dict = {i: self.global_reward for i in range(self.get_num_agents())}

        if (self._max_episode_steps is not None) and (self._elapsed_steps >= self._max_episode_steps):
            self.dones["__all__"] = True
            for k in self.dones.keys():
                self.dones[k] = True

        action_required_agents = {
            i: self.agents[i].speed_data['position_fraction'] == 0.0 for i in range(self.get_num_agents())
        }
        malfunction_agents = {
            i: self.agents[i].malfunction_data['malfunction'] for i in range(self.get_num_agents())
        }
        speed_agents = {i: self.agents[i].speed_data['speed'] for i in range(self.get_num_agents())}

        info_dict = {
            'action_required': action_required_agents,
            'malfunction': malfunction_agents,
            'speed': speed_agents
        }

        return self._get_observations(), self.rewards_dict, self.dones, info_dict

    def _step_agent(self, i_agent, action: Optional[RailEnvActions] = None):
        """
        Performs a step and step, start and stop penalty on a single agent in the following sub steps:
        - malfunction
        - action handling if at the beginning of cell
        - movement

        Parameters
        ----------
        i_agent : int
        action_dict_ : Dict[int,RailEnvActions]

        """
        if self.dones[i_agent]:  # this agent has already completed...
            return

        agent = self.agents[i_agent]
        agent.old_direction = agent.direction
        agent.old_position = agent.position

        # is the agent malfunctioning?
        malfunction = self._agent_malfunction(i_agent)

        # if agent is broken, actions are ignored and agent does not move.
        # full step penalty in this case
        if malfunction:
            self.rewards_dict[i_agent] += self.step_penalty * agent.speed_data['speed']
            return

        # Is the agent at the beginning of the cell? Then, it can take an action.
        # As long as the agent is malfunctioning or stopped at the beginning of the cell, different actions may be taken!
        if agent.speed_data['position_fraction'] == 0.0:
            # No action has been supplied for this agent -> set DO_NOTHING as default
            if action is None:
                action = RailEnvActions.DO_NOTHING

            if action < 0 or action > len(RailEnvActions):
                print('ERROR: illegal action=', action,
                      'for agent with index=', i_agent,
                      '"DO NOTHING" will be executed instead')
                action = RailEnvActions.DO_NOTHING

            if action == RailEnvActions.DO_NOTHING and agent.moving:
                # Keep moving
                action = RailEnvActions.MOVE_FORWARD

            if action == RailEnvActions.STOP_MOVING and agent.moving:
                # Only allow halting an agent on entering new cells.
                agent.moving = False
                self.rewards_dict[i_agent] += self.stop_penalty

            if not agent.moving and not (
                action == RailEnvActions.DO_NOTHING or action == RailEnvActions.STOP_MOVING):
                # Allow agent to start with any forward or direction action
                agent.moving = True
                self.rewards_dict[i_agent] += self.start_penalty

            # Store the action if action is moving
            # If not moving, the action will be stored when the agent starts moving again.
            if agent.moving:
                _action_stored = False
                _, new_cell_valid, new_direction, new_position, transition_valid = \
                    self._check_action_on_agent(action, agent)

                if all([new_cell_valid, transition_valid]):
                    agent.speed_data['transition_action_on_cellexit'] = action
                    _action_stored = True
                else:
                    # But, if the chosen invalid action was LEFT/RIGHT, and the agent is moving,
                    # try to keep moving forward!
                    if (action == RailEnvActions.MOVE_LEFT or action == RailEnvActions.MOVE_RIGHT):
                        _, new_cell_valid, new_direction, new_position, transition_valid = \
                            self._check_action_on_agent(RailEnvActions.MOVE_FORWARD, agent)

                        if all([new_cell_valid, transition_valid]):
                            agent.speed_data['transition_action_on_cellexit'] = RailEnvActions.MOVE_FORWARD
                            _action_stored = True

                if not _action_stored:

                    # If the agent cannot move due to an invalid transition, we set its state to not moving
                    self.rewards_dict[i_agent] += self.invalid_action_penalty
                    self.rewards_dict[i_agent] += self.stop_penalty
                    agent.moving = False

        # Now perform a movement.
        # If agent.moving, increment the position_fraction by the speed of the agent
        # If the new position fraction is >= 1, reset to 0, and perform the stored
        #   transition_action_on_cellexit if the cell is free.
        if agent.moving:
            agent.speed_data['position_fraction'] += agent.speed_data['speed']
            if agent.speed_data['position_fraction'] >= 1.0:
                # Perform stored action to transition to the next cell as soon as cell is free
                # Notice that we've already checked new_cell_valid and transition valid when we stored the action,
                # so we only have to check cell_free now!

                # cell and transition validity was checked when we stored transition_action_on_cellexit!
                cell_free, new_cell_valid, new_direction, new_position, transition_valid = self._check_action_on_agent(
                    agent.speed_data['transition_action_on_cellexit'], agent)

                # N.B. validity of new_cell and transition should have been verified before the action was stored!
                assert new_cell_valid
                assert transition_valid
                if cell_free:
                    agent.position = new_position
                    agent.direction = new_direction
                    agent.speed_data['position_fraction'] = 0.0

            # has the agent reached its target?
            if np.equal(agent.position, agent.target).all():
                self.dones[i_agent] = True
                agent.moving = False
            else:
                self.rewards_dict[i_agent] += self.step_penalty * agent.speed_data['speed']
        else:
            # step penalty if not moving (stopped now or before)
            self.rewards_dict[i_agent] += self.step_penalty * agent.speed_data['speed']

    def _check_action_on_agent(self, action: RailEnvActions, agent: EnvAgent):
        """

        Parameters
        ----------
        action : RailEnvActions
        agent : EnvAgent

        Returns
        -------
        bool
            Is it a legal move?
            1) transition allows the new_direction in the cell,
            2) the new cell is not empty (case 0),
            3) the cell is free, i.e., no agent is currently in that cell


        """
        # compute number of possible transitions in the current
        # cell used to check for invalid actions
        new_direction, transition_valid = self.check_action(agent, action)
        new_position = get_new_position(agent.position, new_direction)

        new_cell_valid = (
            np.array_equal(  # Check the new position is still in the grid
                new_position,
                np.clip(new_position, [0, 0], [self.height - 1, self.width - 1]))
            and  # check the new position has some transitions (ie is not an empty cell)
            self.rail.get_full_transitions(*new_position) > 0)

        # If transition validity hasn't been checked yet.
        if transition_valid is None:
            transition_valid = self.rail.get_transition(
                (*agent.position, agent.direction),
                new_direction)

        # Check the new position is not the same as any of the existing agent positions
        # (including itself, for simplicity, since it is moving)
        cell_free = not np.any(np.equal(new_position, [agent2.position for agent2 in self.agents]).all(1))
        return cell_free, new_cell_valid, new_direction, new_position, transition_valid

    def check_action(self, agent: EnvAgent, action: RailEnvActions):
        """

        Parameters
        ----------
        agent : EnvAgent
        action : RailEnvActions

        Returns
        -------
        Tuple[Grid4TransitionsEnum,Tuple[int,int]]



        """
        transition_valid = None
        possible_transitions = self.rail.get_transitions(*agent.position, agent.direction)
        num_transitions = np.count_nonzero(possible_transitions)

        new_direction = agent.direction
        if action == RailEnvActions.MOVE_LEFT:
            new_direction = agent.direction - 1
            if num_transitions <= 1:
                transition_valid = False

        elif action == RailEnvActions.MOVE_RIGHT:
            new_direction = agent.direction + 1
            if num_transitions <= 1:
                transition_valid = False

        new_direction %= 4

        if action == RailEnvActions.MOVE_FORWARD and num_transitions == 1:
            # - dead-end, straight line or curved line;
            # new_direction will be the only valid transition
            # - take only available transition
            new_direction = np.argmax(possible_transitions)
            transition_valid = True
        return new_direction, transition_valid

    @staticmethod
    def get_valid_move_actions_(agent_direction: Grid4TransitionsEnum,
                                agent_position: Tuple[int, int],
                                rail: GridTransitionMap) -> Set[RailEnvNextAction]:
        """
        Get the valid move actions (forward, left, right) for an agent.

        Parameters
        ----------
        agent_direction : Grid4TransitionsEnum
        agent_position: Tuple[int,int]
        rail : GridTransitionMap


        Returns
        -------
        Set of `RailEnvNextAction` (tuples of (action,position,direction))
            Possible move actions (forward,left,right) and the next position/direction they lead to.
            It is not checked that the next cell is free.
        """
        valid_actions: Set[RailEnvNextAction] = OrderedSet()
        possible_transitions = rail.get_transitions(*agent_position, agent_direction)
        num_transitions = np.count_nonzero(possible_transitions)
        # Start from the current orientation, and see which transitions are available;
        # organize them as [left, forward, right], relative to the current orientation
        # If only one transition is possible, the forward branch is aligned with it.
        if rail.is_dead_end(agent_position):
            action = RailEnvActions.MOVE_FORWARD
            exit_direction = (agent_direction + 2) % 4
            if possible_transitions[exit_direction]:
                new_position = get_new_position(agent_position, exit_direction)
                valid_actions.add(RailEnvNextAction(action, new_position, exit_direction))
        elif num_transitions == 1:
            action = RailEnvActions.MOVE_FORWARD
            for new_direction in [(agent_direction + i) % 4 for i in range(-1, 2)]:
                if possible_transitions[new_direction]:
                    new_position = get_new_position(agent_position, new_direction)
                    valid_actions.add(RailEnvNextAction(action, new_position, new_direction))
        else:
            for new_direction in [(agent_direction + i) % 4 for i in range(-1, 2)]:
                if possible_transitions[new_direction]:
                    if new_direction == agent_direction:
                        action = RailEnvActions.MOVE_FORWARD
                    elif new_direction == (agent_direction + 1) % 4:
                        action = RailEnvActions.MOVE_RIGHT
                    elif new_direction == (agent_direction - 1) % 4:
                        action = RailEnvActions.MOVE_LEFT
                    else:
                        raise Exception("Illegal state")

                    new_position = get_new_position(agent_position, new_direction)
                    valid_actions.add(RailEnvNextAction(action, new_position, new_direction))
        return valid_actions

    def _get_observations(self):
        self.obs_dict = self.obs_builder.get_many(list(range(self.get_num_agents())))
        return self.obs_dict

    def get_full_state_msg(self):
        grid_data = self.rail.grid.tolist()
        agent_static_data = [agent.to_list() for agent in self.agents_static]
        agent_data = [agent.to_list() for agent in self.agents]
        msgpack.packb(grid_data, use_bin_type=True)
        msgpack.packb(agent_data, use_bin_type=True)
        msgpack.packb(agent_static_data, use_bin_type=True)
        msg_data = {
            "grid": grid_data,
            "agents_static": agent_static_data,
            "agents": agent_data}
        return msgpack.packb(msg_data, use_bin_type=True)

    def get_agent_state_msg(self):
        agent_data = [agent.to_list() for agent in self.agents]
        msg_data = {
            "agents": agent_data}
        return msgpack.packb(msg_data, use_bin_type=True)

    def set_full_state_msg(self, msg_data):
        data = msgpack.unpackb(msg_data, use_list=False, encoding='utf-8')
        self.rail.grid = np.array(data["grid"])
        # agents are always reset as not moving
        self.agents_static = [EnvAgentStatic(d[0], d[1], d[2], moving=False) for d in data["agents_static"]]
        self.agents = [EnvAgent(d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8]) for d in data["agents"]]
        # setup with loaded data
        self.height, self.width = self.rail.grid.shape
        self.rail.height = self.height
        self.rail.width = self.width
        self.dones = dict.fromkeys(list(range(self.get_num_agents())) + ["__all__"], False)

    def set_full_state_dist_msg(self, msg_data):
        data = msgpack.unpackb(msg_data, use_list=False, encoding='utf-8')
        self.rail.grid = np.array(data["grid"])
        # agents are always reset as not moving
        self.agents_static = [EnvAgentStatic(d[0], d[1], d[2], moving=False) for d in data["agents_static"]]
        self.agents = [EnvAgent(d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8]) for d in data["agents"]]
        if "distance_map" in data.keys():
            self.distance_map.set(data["distance_map"])
        # setup with loaded data
        self.height, self.width = self.rail.grid.shape
        self.rail.height = self.height
        self.rail.width = self.width
        self.dones = dict.fromkeys(list(range(self.get_num_agents())) + ["__all__"], False)

    def get_full_state_dist_msg(self):
        grid_data = self.rail.grid.tolist()
        agent_static_data = [agent.to_list() for agent in self.agents_static]
        agent_data = [agent.to_list() for agent in self.agents]
        msgpack.packb(grid_data, use_bin_type=True)
        msgpack.packb(agent_data, use_bin_type=True)
        msgpack.packb(agent_static_data, use_bin_type=True)
        distance_map_data = self.distance_map.get()
        msgpack.packb(distance_map_data, use_bin_type=True)
        msg_data = {
            "grid": grid_data,
            "agents_static": agent_static_data,
            "agents": agent_data,
            "distance_map": distance_map_data}

        return msgpack.packb(msg_data, use_bin_type=True)

    def save(self, filename):
        if self.distance_map.get() is not None:
            if len(self.distance_map.get()) > 0:
                with open(filename, "wb") as file_out:
                    file_out.write(self.get_full_state_dist_msg())
            else:
                with open(filename, "wb") as file_out:
                    file_out.write(self.get_full_state_msg())
        else:
            with open(filename, "wb") as file_out:
                file_out.write(self.get_full_state_msg())

    def load(self, filename):
        with open(filename, "rb") as file_in:
            load_data = file_in.read()
            self.set_full_state_dist_msg(load_data)

    def load_pkl(self, pkl_data):
        self.set_full_state_msg(pkl_data)

    def load_resource(self, package, resource):
        from importlib_resources import read_binary
        load_data = read_binary(package, resource)
        self.set_full_state_msg(load_data)
