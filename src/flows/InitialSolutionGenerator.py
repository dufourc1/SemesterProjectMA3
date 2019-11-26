# given as input a time expanded network with sources and sinks and the constraints
# compute an initial feasible solution

import networkx as nx
from copy import deepcopy
from tqdm import tqdm
import numpy as np
import time
import pprint

from src.flows.time_evolving_network import TimeNetwork
from src.flows.NFirstShortestPaths import PathFinder


class InitialSolutionGenerator:

	def __init__(self, ten:TimeNetwork, constraints, numberOfCommodities):
		'''		
		Parameters
		----------
		ten : TimeNetwork
			time expanded network with sources and sinks with names are source_... and sink_...
		constraints : list of sets
			constraints the edges (only one edge of each set can be activated at the same time)
		'''

		#save data
		self.constraints = constraints
		self.graph = deepcopy(ten.graph)
		

		#get sources and sinks from the graph as a preprocessing step
		self.sinks = []
		self.sources = []
		self.stats = {}
		self.stats["time for pathFinder: "] = []
		self.stats["time for checkCollision: "] = []
		self.stats["not shortest path "] = 0

		#extract and order the sources/sinks 
		for i in range(numberOfCommodities):
			self.sources.append("source_"+str(i))
			self.sinks.append("sink_"+str(i))

		#sanity check 
		try:
			test = self.graph.nodes[self.sources[-1]]
			test = self.graph.nodes[self.sinks[-1]]
		except:
			print(f"you probably fucked up something in the number of sources and sinks (got {numberOfCommodities})")	
			print(f"Did you check that the names were correct ? I expect something like {self.sources[-1]} and {self.sinks[-1]} but could not find them")
			raise ValueError("Error, could not fetch the sources and sinks")


		#initialize a path finder
		self.pathFinder = PathFinder(self.graph)

		#create empty solutions 
		self.solution = []
		
	def getInitialSolution(self):
		'''
		return a feasible initial solution using a greedy algorithm
		'''
		start = time.time()
		#go over all pairs of source-sink
		for s,t in tqdm(zip(self.sources,self.sinks)):

			start_inter = time.time()
			#find all the paths in order from shortest to longest
			paths = self.pathFinder.findShortestPaths(s,t,5)
			stop_inter = time.time()-start_inter
			self.stats["time for pathFinder: "].append(round(stop_inter,2))

			# if there is an issue we just take the next candidate graph
			# otherwise we add it to the solution and we stop iterating over the candidates
			for p in paths:
				start_inter_2 = time.time()
				if self.checkIssues(p):
					self.solution.append(p)
					break
					self.stats["time for checkCollision: "].append(round(time.time()-start_inter_2,3))
				else:
					self.stats["time for checkCollision: "].append(round(time.time()-start_inter_2,3))
					self.stats["not shortest path "] += 1
		self.stats["total time to solution: "] = time.time()-start
		return self.solution

	def  checkIssues(self, path):
		'''
		check if we can add the path to already chosen paths
		given the constraints
		
		Parameters
		----------
		path : array
			list of edges representing a path
		
		Returns
		-------
		Boolean
			True if no issues are detected
			False if there is an issue wrt to the constraints
		'''

		#if this is the first solution we add there are no problem
		if len(self.solution) == 0:
			return True

		#check for each already added path if there is a problem 
		for p in self.solution:
			if self.collision(path,p):
				return False

		return True

		
	def collision(self,p1,p2):
		'''
		check that p1 and p2 are compatible wrt to the constraints 
		return True if a collision is detected
		
		Parameters
		----------
		p1 : array
			list of edges representing a path
		p2 : array
			list of edges representing a path
		
		Returns
		-------
		Boolean
			True if there is a collision between p1 and p2
			False if there are no collisions
		'''
		#TODO: build data structure to accelerate this process

		for c in self.constraints:
			for edge in p1:
				for edge2 in p2:
					if edge in c and edge2 in c:
						return True

		return False
				
	def showStats(self):
		self.stats["time for checkCollision: "] = np.mean(np.array(self.stats["time for checkCollision: "]))
		self.stats["time for pathFinder: "] = np.mean(np.array(self.stats["time for pathFinder: "]))
		pprint.pprint(self.stats)