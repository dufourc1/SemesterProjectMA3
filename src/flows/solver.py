
from src.flows.time_evolving_network import TimeNetwork
from src.graph.NetworkGraph import NetworkGraph
from src.flows.PricingProblem import PricingSolver
from src.flows.InitialSolutionGenerator import InitialSolutionGenerator
from src.flows.MasterProblem import MasterProblem
from src.flows.lp_formulation import MCFlow

import numpy as np
import pandas as pd
import logging
import time
import gurobipy 

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
		self.stats = {}
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
		self.stats = {}
		self.transitionNetwork = NetworkGraph(np.array(env.rail.grid.tolist()))
		self.agents_information(env)
		self.build_time_expanded_network(timeHorizon)
		if self.method == "Column Generation":
			self.setup_column_generation()
		elif self.method == "Arc Formulation":
			print("Setting up the arc formulation may take some time and RAM")
			self.setup_arc_formulation()
		self.logger.info("Building completed")

	def solve(self,env,timeHorizon):
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
		self.build(env,timeHorizon)
		self.logger.info("Solving")
		if self.method == "Column Generation":
			return self.appply_column_generation()
		elif self.method == "Arc Formulation":
			return self.apply_arc_formulation()
		else:
			raise ValueError(f"unknown method {method} to solve the mc flow problem."+
				 "\\Column Generation or  Arc Formulation are implemented.")
		self.logger.info("Solving ended")

	def agents_information(self, env):
		'''
		get necessaries informations to create the commodities
		
		Parameters
		----------
		env : Faltland environment
		'''
		self.sources = []
		self.sinks = []
		self.directions = []
		self.speeds = []
		for agent in env.agents:
			self.sources.append(agent.initial_position)
			self.sinks.append(agent.target)
			self.speeds.append(agent.speed_data['speed'])
			self.directions.append(agent.direction)
		self.numberOfCommodities = len(self.sources)


	def build_time_expanded_network(self, timeHorizon):
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

	def extractSolution(self):
		raise NotImplementedError()

	def setup_column_generation(self):

		self.logger.info("setting up column generation method")
		self.constraints,self.find_constraints = self.timeExpandedNetwork.get_topology_network()
		self.initialSolutionGenerator = InitialSolutionGenerator(self.timeExpandedNetwork,self.constraints,
																 self.find_constraints,self.numberOfCommodities)
		self.logger.info("finished set up for column generation method")

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
		return self.mcflow.m.objVal

	def appply_column_generation(self):
		'''
		solve iteratively IP defined by column generation method
		'''
		self.logger.info("solving with column generation")
		flag = True
		iteration = 1
		self.initialSolution = self.initialSolutionGenerator.getInitialSolution()
		self.master = MasterProblem(self.initialSolution,self.constraints,
											self.find_constraints,self.numberOfCommodities)
		self.master.build()
		pricingSolver = PricingSolver(self.timeExpandedNetwork.graph,self.constraints,
										self.find_constraints,self.numberOfCommodities)
		while flag:
			print("iteration ",iteration)
			self.master.solveRelaxedModel()
			duals = self.master.getDualVariables()
			pathsToAdd, flag = pricingSolver.get_columns_to_add(self.master.getDualVariables(),
																self.master.constraintsActivated)
			if flag:
				#pprint.pprint(pathsToAdd)
				print(f" commodities with updated paths: {pathsToAdd.keys()}")
				iteration+= 1
				self.master.addColumn(pathsToAdd)
		self.logger.info(f"finished solving with column generation after {iteration} iterations")
		self.master.model.optimize()
		if self.verbose:
			print(f"score: {self.master.model.objVal}")
		self.logger.info("finished solving integer formulation")

		return self.master.model.objVal
