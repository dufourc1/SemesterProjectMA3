
from src.flows.time_evolving_network import TimeNetwork
from src.graph.NetworkGraph import NetworkGraph
from src.flows.PricingProblem import PricingSolver
from src.flows.InitialSolutionGenerator import InitialSolutionGenerator
from src.flows.MasterProblem import MasterProblem
from src.flows.lp_formulation import MCFlow
from src.navigation.navigation_path import walk_many_paths

import numpy as np
import pandas as pd
import logging
import time
import gurobipy 
import collections

def parse_tuple_from_txt(tuple_str):
    interest = tuple_str.split("_")[0]
    interest_left = interest.split("(")[1].split(",")[0]
    interest_right = interest.split(")")[0].split(",")[1]
    return (int(interest_left),int(interest_right))
class Solver:

	def __init__(self, logfile, method = "Column Generation",useDirections = False, useSpeeds = False,verbose = True):
		'''
		
		
		Parameters
		----------
		logfile : string
			name to a file where the logs of the solver will be saved (if it does not exist it is created)
		method : str, optional
			choose which method to solve the routing problem, either "Column Generation" or "Arc Fromulation",
			 by default "Column Generation"
		useDirections : bool, optional
			use directions of agent to connect agents to the time expanded network, by default False
		useSpeeds : bool, optional
			NOT IMPLEMENTED YET, by default False
		verbose : bool, optional
			Allow printing to the console, by default True
		'''
		self.stats = {"timeInit": None}
		self.verbose = verbose
		self.useDirections = useDirections
		self.useSpeeds = useSpeeds
		self.logfile = logfile
		self.method = method
		logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, filename = logfile, filemode = 'a')
		self.logger = logging.getLogger("solver")
		self.logger.info(f"New solver created of type {self.method}")

	def build(self, env, timeHorizon):
		'''
		build the necessary data structure to solve the routing problem (TEN, dictionaries,...)
		
		Parameters
		----------
		env : Flatland environment
		timeHorizon : int
			the length to build the time expanded network
		'''
					
		self.logger.info(f"Building solver with {self.method} and a time expanded network of size {timeHorizon}")
		self.stats = {"timeInit": None}
		self.iterations = 0
		self.transitionNetwork = NetworkGraph(np.array(env.rail.grid.tolist()))
		self.agents_information(env)
		self.build_time_expanded_network(timeHorizon)
		if self.method == "Column Generation":
			self.setup_column_generation()
		elif self.method == "Arc Formulation":
			print("Setting up the arc formulation may take some time and RAM")
			self.setup_arc_formulation()
		self.logger.info("Building completed")

	def solve(self,env,timeHorizon = None):
		'''
		solve the multicommodity flow problem and keep the results in memory
		
		Parameters
		----------
		env : Flatland environment
		timeHorizon : int
			the length to build the time expanded network

		Returns
		-------
		score (objective function of the integer program)
		
		Raises
		------
		ValueError
			if method of solver is not implemented
		'''
		self.max_time_steps = 4 * 2 * (env.width + env.height + 20)
		if timeHorizon is None:
			timeHorizon = self.max_time_steps
		start = time.time()
		self.build(env,timeHorizon)
		self.stats["running time"] = start

		self.logger.info("Solving")

		if self.method == "Column Generation":
			return self.appply_column_generation()
		elif self.method == "Arc Formulation":
			return self.apply_arc_formulation()
		else:
			raise ValueError(f"unknown method {method} to solve the mc flow problem."+
				 "\\Column Generation or  Arc Formulation are implemented.")
		

	def agents_information(self, env):
		'''
		get necessaries informations to create the commodities
		
		Parameters
		----------
		env : Faltland environment
		'''
		info,agent_to_drop = self.check_env(env)
		self.to_drop = agent_to_drop
		self.dropped = [a.handle for a in agent_to_drop]
		self.dealt_with = [True for i in env.agents]
		if len(agent_to_drop) >0:
			print(f"Had to drop {len(agent_to_drop)} agents, conflict with their starting position")
			print([a.handle for a in agent_to_drop])
			print(f" configuration is to clean problematic agent, deleting agent from env")
			self.clean_env(env,self.to_drop)
		self.sources = []
		self.sinks = []
		self.directions = []
		self.speeds = []
		for agent in env.agents:
			if agent not in agent_to_drop:
				self.sources.append(agent.initial_position)
				self.sinks.append(agent.target)
				self.speeds.append(agent.speed_data['speed'])
				self.directions.append(agent.direction)
			else:
				self.dealt_with[agent.handle] = False
		self.numberOfCommodities = len(self.sources)


	def build_time_expanded_network(self, timeHorizon= None):
		'''
		Build the time expanded network and get data structure for 
		constraints handling (constraints (set) and dicitonnary to track edge to constraint)
		
		Parameters
		----------
		timeHorizon : int
		'''


		self.logger.info("Building time expanded network")
		self.timeExpandedNetwork = TimeNetwork(self.transitionNetwork,depth = timeHorizon)
		if self.useDirections:
			self.timeExpandedNetwork.connect_sources_and_sink(self.sources,self.sinks,self.directions)
		else:
			self.timeExpandedNetwork.connect_sources_and_sink(self.sources,self.sinks)

		self.logger.info("Finished building time expanded network")



	def setup_column_generation(self):

		self.logger.info("Setting up column generation method")
		self.constraints,self.find_constraints = self.timeExpandedNetwork.get_topology_network()
		self.logger.info("Got the constraints")
		self.initialSolutionGenerator = InitialSolutionGenerator(self.timeExpandedNetwork,self.constraints,
																 self.find_constraints,self.numberOfCommodities)
		self.logger.info("Initial solution algorithm ready")
		self.logger.info("Finished set up for column generation method")

	def setup_arc_formulation(self):

		self.logger.info("setting up for arc formulation")
		self.constraints,self.find_constraints = self.timeExpandedNetwork.get_topology_network()
		try:
			self.mcflow = MCFlow(self.timeExpandedNetwork.graph,self.numberOfCommodities,self.constraints,integer = True)
			self.logger.info("finished set up for arc formulation")
		except :
			self.logger.error("arc formulation setup failed")


	def apply_arc_formulation(self):
		'''
		solve IP defined by arc formulation
		'''
		self.logger.info("solving with arc formulation")
		self.mcflow.solve()
		if self.verbose:
			print(f"score: {self.mcflow.m.objVal}")
		self.logger.info("finished solving with arc formulation")
		self.stats["running time"] = time.time()- self.stats["running time"]
		self.solution_cell = self.mcflow.get_paths_solution()
		return self.mcflow.m.objVal

	def appply_column_generation(self):
		'''
		solve iteratively IP defined by column generation method
		'''
		self.logger.info("solving with column generation")
		flag = True
		iteration = 1
		start = time.time()
		self.initialSolution = self.initialSolutionGenerator.getInitialSolution()
		self.stats["timeInit"] = time.time()-start
		self.logger.info("got initial solution")
		self.master = MasterProblem(self.initialSolution,self.constraints,
											self.find_constraints,self.numberOfCommodities)
		self.master.build()
		pricingSolver = PricingSolver(self.timeExpandedNetwork.graph,self.constraints,
										self.find_constraints,self.numberOfCommodities)
		while flag:
			self.master.solveRelaxedModel()
			duals = self.master.getDualVariables()
			pathsToAdd, flag = pricingSolver.get_columns_to_add(self.master.getDualVariables(),
																self.master.constraintsActivated)
			if flag:
				iteration+= 1
				self.iterations += 1
				self.master.addColumn(pathsToAdd)
		self.logger.info(f"finished solving with column generation after {iteration} iterations")
		self.master.model.optimize()
		self.stats["running time"] = time.time()- self.stats["running time"]
		if self.verbose:
			print(f"score: {self.master.model.objVal}")
		self.solution_edge = self.translate_edges_ten_to_edge_transition(self.master.get_solution())
		self.solution_cell = self.translate_edges_ten_to_cell_list(self.master.get_solution())
		self.logger.info("finished solving integer formulation")
		
		return self.master.model.objVal

	
	def translate_edges_ten_to_cell_list(self,paths_dict):
		result = {}
		for c,path in paths_dict.items():
			inter_list = [parse_tuple_from_txt(x[1].split("_t")[0]) for x in path if not x[1].startswith("sink")]
			result[c] = [inter_list[2*i] for i in range(int(len(inter_list)/2))]
			result[c].append(inter_list[-1])
		return result


	def translate_edges_ten_to_edge_transition(self,paths_dict):
		result = {}
		for c,path in paths_dict.items():
			result[c] = [(x[0].split("_t")[0],x[1].split("_t")[0]) for x in path if not x[0].startswith("source") and not x[1].startswith("sink")]
		return result


	def prepare_paths(self,env):
		paths = [path for _,path in self.solution_cell.items()]

		paths_to_run = list(np.repeat([],self.numberOfCommodities))
		index  = 0
		for elt in self.dealt_with:
			if elt:
				paths_to_run.append(paths[index])
				index += 1
			else:
				paths_to_run.append([])
		return paths_to_run

	def run(self,env,envRenderer):
		self.clean_env(env,self.to_drop)
		paths = [path for _,path in collections.OrderedDict(sorted(self.solution_cell.items())).items()]
		for elt in self.dropped:
			paths.insert(elt,[])
		walk_many_paths(env,envRenderer,paths)


	def check_env(self,env):
		info = {}
		agents_to_drop = []
		for agent in env.agents:
			if agent.initial_position in info.keys():
				info[agent.initial_position]["number"] += 1
				info[agent.initial_position]["agents"].append(agent.handle)
				agents_to_drop.append(agent)
			else:
				info[agent.initial_position] = {}
				info[agent.initial_position]["number"] = 1
				info[agent.initial_position]["agents"] = [agent.handle]
		return info,agents_to_drop
	
	def clean_env(self,env,agents_to_drop):
		env.restart_agents()
		#env.agents = [a for a in env.agents if a not in agents_to_drop]