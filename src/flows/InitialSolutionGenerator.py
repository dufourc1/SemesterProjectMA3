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

	def __init__(self, ten:TimeNetwork, constraints, findConstraints, numberOfCommodities):
		'''		
		Parameters
		----------
		ten : TimeNetwork
			time expanded network with sources and sinks with names are source_0 and sink_0
		constraints : list of sets
			constraints the edges (only one edge of each set can be activated at the same time)
		findConstraints: dict
			findConstraints[edge] returns a list of constraint to which the edge belongs
		numberOfCommodities: int
		'''

		#save data
		self.constraints = constraints
		self.findConstraints = findConstraints
		self.graph = ten.graph
		

		#get sources and sinks from the graph as a preprocessing step
		self.sinks = []
		self.sources = []
		self.stats = {}

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

		self.solution = []
		self.stats = {}
		#go over all pairs of source-sink
		for i,(s,t) in tqdm(enumerate(zip(self.sources,self.sinks))):

			#ensure we find a feasible solution for each commodity
			NotFound = True
	
			while NotFound:
				paths = self.pathFinder.findShortestPaths(s,t,5)
				# if there is an issue we just take the next candidate graph
				# otherwise we add it to the solution and we stop iterating over the candidates
				for p in paths:
					start_inter_2 = time.time()
					if self.checkIssues(p):
						self.solution.append(p)
						NotFound = False
						break
					else:
						if f"not shortest path for {i}" not in self.stats.keys():
							self.stats[f"not shortest path for {i}"] = 1
						else:
							self.stats[f"not shortest path for {i}"] += 1
					

			#reset all the weights since we change commodity
			self.pathFinder.reset_weights()

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


		#do not look at the source and sink connected edges since 
		
		for edge in p1:
			if "source" not in edge[0] and "sink" not in edge[1]:
				c1 = self.findConstraints[edge]
				for edge2 in p2:
					if "source" not in edge2[0] and "sink" not in edge2[1]:
						c2 = self.findConstraints[edge2]
						if len([x for x in c1 if x in c2])>0:
							return True

		return False
				
	def showStats(self):
		pprint.pprint(self.stats)