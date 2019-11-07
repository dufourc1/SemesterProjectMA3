import gurobipy
import numpy as np
import networkx as nx
import copy
from tqdm import tqdm
import time

class MCFlow:

	def __init__(self, graph,numberOfCommodities, topology):
		'''
		build the gurobipy models and add the constraints specified in self.__add_constraints()
		
		Parameters
		----------
		timeNetwork: TimeNetwork
			Time expanded Network containing a graph
			
			graph on which to run the multicommodity flow problem
			should have source and sink nodes annotated like "source_agent_1", "sink_agent_1" 
			should have edges with both weight and capacity

		numberOfCommodities : int
			number of commodities in that can be found if going through all the sources and sinks in the graph

		topology: list of set of edges of the original graph
			additional constraints, put an empty list of not wanted
		'''

		#extract the graph from the time evolving network
		

		#build the two principal lists
		self.commodities = np.arange(0,numberOfCommodities)
		self.nodes = graph.nodes

		#get the arcs and the capacity from the graph
		self.arcs,self.capacity = gurobipy.multidict(self.__get_dict_arcs_capacity(graph))


		#get the cost of each arcs
		self.cost = self.__get_dict_cost_per_commodity_per_arc(graph)

		#get the demand for the pairs commodity-vertex
		self.inflow = self.__get_dict_inflow(graph)

		#create a gurobipy model 
		self.m = gurobipy.Model('netflow')

		#create the variables 
		self.flow = self.m.addVars(self.commodities, self.arcs, obj = self.cost, name = 'flow',vtype=gurobipy.GRB.BINARY)

		#add the constraint to the model
		self.__add_constraints(topology)

		self.solution = None
		self.solution_complete = None


	
	def solve(self):
		'''
		solve the linear programming instance using gurobipy
		'''
		self.m.optimize()
		self.solution_complete = self.__extract_paths().copy()
		self.solution = self.__translate_path_to_cell_coordinate(self.solution_complete)
		if not self.check_no_collisions_solution(self.solution):
			raise ValueError("collisions detected")

	def show_results(self):
		'''
		print the result if an optimal solution was found
		'''
		if self.m.status == gurobipy.GRB.Status.OPTIMAL:
			solution = self.m.getAttr('x', self.flow)
			for h in self.commodities:
				print('\nOptimal flows for %s:' % h)
				for i,j in self.arcs:
					if solution[h,i,j] > 0:
						print('%s -> %s: %g' % (i, j, solution[h,i,j]))
		else:
			print("model not optimized or failed to optimize \n please use .solve() and check the output")


	def __get_dict_inflow(self,graph):
		'''
		Demand for pairs of commodity-city

		
		Parameters
		----------
		graph : nx.Digraph
		
		Return
		------
		dict
			e.g.{
					('Pencils', 'Detroit'):   50,
					('Pencils', 'Denver'):    60,
					('Pencils', 'Boston'):   -50,
					('Pencils', 'New York'): -50,
					('Pencils', 'Seattle'):  -10,
					('Pens',    'Detroit'):   60,
					('Pens',    'Denver'):    40,
					('Pens',    'Boston'):   -40,
					('Pens',    'New York'): -30,
					('Pens',    'Seattle'):  -30 
				}
		'''

		inflow = {}
		for node in self.nodes:
			for commodity in self.commodities:
				if node.startswith("source") and int(node[-1]) == commodity:
					inflow[(int(node[-1]),node)] = 1
				elif node.startswith("sink") and int(node[-1]) == commodity:
					inflow[(int(node[-1]),node)] = -1
				else:
					inflow[(commodity,node)] = 0


		
		return inflow


	def __get_dict_cost_per_commodity_per_arc(self,graph):
		'''
		Cost for triplets commodity-source-destination

		the weight is assumed to be the same for all commodities
		
		Parameters
		----------
		graph : nx.Digraph
		
		Return
		-------
		dict
			like {
					('Pencils', 'Detroit', 'Boston'):   10,
					('Pencils', 'Detroit', 'New York'): 20,
					('Pencils', 'Detroit', 'Seattle'):  60,
					('Pencils', 'Denver',  'Boston'):   40,
					('Pencils', 'Denver',  'New York'): 40,
					('Pencils', 'Denver',  'Seattle'):  30,
					('Pens',    'Detroit', 'Boston'):   20,
					('Pens',    'Detroit', 'New York'): 20,
					('Pens',    'Detroit', 'Seattle'):  80,
					('Pens',    'Denver',  'Boston'):   60,
					('Pens',    'Denver',  'New York'): 70,
					('Pens',    'Denver',  'Seattle'):  30 
				}
		'''

		cost_dict = {}
		
		for edge in graph.edges:
			for commodity in self.commodities:
				cost_dict[(commodity,edge[0],edge[1])] = graph.edges[edge]['weight']

		return cost_dict

	def __get_dict_arcs_capacity(self, graph):
		'''
		get the graph as a input and ouput a dictionnary like
		
		Parameters
		----------
		graph : nx.Digraph
				graph on which to run the multicommodity flow problem
		
		Return
		------
		dict
			dictionnary to build gurobipy model like
			{
				('Detroit', 'Boston'):   100,
				('Boston','Detroit'):   30,
				('Detroit', 'New York'):  80,
				('Detroit', 'Seattle'):  120,
				('Denver',  'Boston'):   120,
				('Denver',  'New York'): 120,
				('Denver',  'Seattle'):  120 
			}
		'''

		arcs_capacity = {}

		for edge in graph.edges:
			for commodity in self.commodities:
				arcs_capacity[(edge[0],edge[1])] = graph.edges[edge]['capacity']
		

		return arcs_capacity

	def __add_constraints(self, topology):
		'''
		add the constraints for the LP problem

		
		Parameters
		----------
		topology : list of set of edges of the original graph
			for each set, the sum over the commodities and over the element of 
			this set of the flow will be smaller than 1
		'''
		# Arc-capacity constraints
		self.__add_capacity_constraints()

		# Flow-conservation constraints
		self.__add_flow_conservation_constraints()

		#add topology constraints
		self.__add_topology_constraints(topology)

		
	def __add_capacity_constraints(self):
		'''
		add the capacity constraint accordingly to the ard capacity constraint
		'''
		self.m.addConstrs(
			(self.flow.sum('*',i,j) <= self.capacity[i,j] for i,j in self.arcs), "cap")
		# Equivalent version using Python looping
		# for i,j in arcs:
		#   m.addConstr(sum(flow[h,i,j] for h in commodities) <= capacity[i,j],
		#               "cap[%s,%s]" % (i, j))

	def __add_flow_conservation_constraints(self):
		'''
		add the flow conservation constraint according to the different sources, sinks and transshipment nodes
		'''
		self.m.addConstrs(
			(self.flow.sum(k,'*',j) + self.inflow[k,j] == self.flow.sum(k,j,'*')
			for k in self.commodities for j in self.nodes), "flow")
		
		# Alternate version:
		# m.addConstrs(
		#    (quicksum(flow[h,i,j] for i,j in arcs.select('*',j)) + inflow[h,j] ==
		#      quicksum(flow[h,j,k] for j,k in arcs.select(j,'*'))
		#      for h in commodities for j in nodes), "node")

	def __add_topology_constraints(self,topology):
		'''
		add the constraints to the MCflow LP formulation to take into account that 
		two different nodes in the graph may represent to faces from the same "physical place"
		hence avoiding conflicts between commodity for this "physical place"
		
		Parameters
		----------
		topology : list
			list of disjoint set representing the relation (topology) between the nodes
		'''
		
		
		#for i,set_constraints in enumerate(topology):
		self.m.addConstrs((gurobipy.quicksum(self.flow[h,i,j] for i,j in topology[i] for h in self.commodities) <= 1  for i in range(len(topology))  ) ,"topo")
			
	

	def __check_if_feasible(self):
		'''
		if run after self.solve(), return True if the model was solvable
		'''
		return self.m.status == gurobipy.GRB.Status.OPTIMAL

	def __extract_paths(self):
		'''
		extract the path from the LP into a sequence of visited vertex in the time expanded network
		
		Returns
		-------
		dict
			key: agent, item: path
		'''

		#check if the model has a solution
		if self.__check_if_feasible():
			paths = {}

			#get the solution
			solution = self.m.getAttr('x', self.flow)

			#get the path for each commodities
			for k in self.commodities:
				paths[k] = []
				for i,j in self.arcs:
					if solution[k,i,j] == 1:
						if i.startswith("source"):
						 	paths[k].append(j)
						elif j.startswith("sink"):
						 	paths[k].append(i)
						else:
							paths[k].append(i)
							paths[k].append(j)
						

					elif solution[k,i,j] != 0:
						print("Warning, solution is NOT integral ! ")

			for k,path in paths.items():
				path.sort(key=lambda x: int(x.split("_t")[-1]))
				one_endpoint_seen = {}
				clean_path = []
				for elt in path:
					if elt not in one_endpoint_seen.keys():
						one_endpoint_seen[elt] = True
						clean_path.append(elt)
					else:
						if not one_endpoint_seen[elt]:
							clean_path.append(elt)
						one_endpoint_seen[elt] = not one_endpoint_seen[elt]


				paths[k] = clean_path


			
										
			return paths
		else:
			print("model not optimized or failed to optimize \n please use .solve() and check the output")
			return {}


	def __translate_path_to_cell_coordinate(self, paths_old):
		'''
		translate the paths in term of internal representation to a sequence of cell coordinate 
		
		Parameters
		----------
		paths : dict
			result from __extract_paths()
		
		Returns
		-------
		dict			
		'''
		paths = copy.deepcopy(paths_old)
		paths_coord = {}
		seen = {}
		for agent ,path in paths.items():
			clean_path = []
			for elt in path:
				if elt.startswith("source") or elt.startswith("sink"):
					pass
				else:
					cell_name = elt.split("_")[0]
					if cell_name not in seen.keys():
						seen[cell_name] = 1
						clean_path.append(cell_name)
					else:
						seen[cell_name] += 1
						if seen[cell_name]%2 != 0:
							clean_path.append(cell_name)
			paths_coord[agent] = clean_path
							
					
		return paths_coord

	def check_no_collisions_solution(self,paths):
		'''
		check that no two paths use the same vertex at the same moment
		
		
		Returns
		-------
		bool
			True if no collision is detected, false otherwise
		'''
		paths_list = []
		for k,item in paths.items():
			paths_list.append(item)
		collision = True

		for i,elt in enumerate(zip(*[n for n in paths_list])):
			if len(elt) != len(set(elt)):
				print(f"collision detected at time {i} : {elt}")
				collision = False
		if not collision: print("no collision detected")
		return collision


	def get_paths_solution(self):
		return self.solution

	def see_solution(self):
		raise NotImplementedError
