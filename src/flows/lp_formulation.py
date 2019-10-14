import gurobipy
import numpy as np
import networkx as nx

class MCFlow:

	def __init__(self, graph,numberOfCommodities, topology):
		'''
		build the gurobipy models and add the constraints specified in self.add_constraints()
		
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
		self.arcs,self.capacity = gurobipy.multidict(self.get_dict_arcs_capacity(graph))


		#get the cost of each arcs
		self.cost = self.get_dict_cost_per_commodity_per_arc(graph)

		#get the demand for the pairs commodity-vertex
		self.inflow = self.get_dict_inflow(graph)

		#create a gurobipy model 
		self.m = gurobipy.Model('netflow')

		#create the variables 
		self.flow = self.m.addVars(self.commodities, self.arcs, obj = self.cost, name = 'flow')

		#add the constraint to the model
		self.add_constraints(topology)


	
	def solve(self):
		'''
		solve the linear programming instance using gurobipy
		'''
		self.m.optimize()

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




	def get_dict_inflow(self,graph):
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


	def get_dict_cost_per_commodity_per_arc(self,graph):
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

	def get_dict_arcs_capacity(self, graph):
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

	def add_constraints(self, topology):
		'''
				add the constraints for the LP problem

		
		Parameters
		----------
		topology : list of set of edges of the original graph
			for each set, the sum over the commodities and over the element of 
			this set of the flow will be smaller than 1
		'''
		# Arc-capacity constraints
		self.add_capacity_constraints()

		# Flow-conservation constraints
		self.add_flow_conservation_constraints()

		#add topology constraints
		self.add_topology_constraints(topology)

		
	def add_capacity_constraints(self):
		'''
		add the capacity constraint accordingly to the ard capacity constraint
		'''
		self.m.addConstrs(
			(self.flow.sum('*',i,j) <= self.capacity[i,j] for i,j in self.arcs), "cap")
		# Equivalent version using Python looping
		# for i,j in arcs:
		#   m.addConstr(sum(flow[h,i,j] for h in commodities) <= capacity[i,j],
		#               "cap[%s,%s]" % (i, j))

	def add_flow_conservation_constraints(self):
		'''
		add the flow conservation constraint according to the different sources, sinks and transshipment nodes
		'''
		self.m.addConstrs(
			(self.flow.sum(k,'*',j) + self.inflow[k,j] == self.flow.sum(k,j,'*')
			for k in self.commodities for j in self.nodes), "flow")
		# Alternate version:
		# m.addConstrs(
		#   (quicksum(flow[h,i,j] for i,j in arcs.select('*',j)) + inflow[h,j] ==
		#     quicksum(flow[h,j,k] for j,k in arcs.select(j,'*'))
		#     for h in commodities for j in nodes), "node")

	def add_topology_constraints(self,topology):
		'''
		add the constraints to the MCflow LP formulation to take into account that 
		two different nodes in the graph may represent to faces from the same "physical place"
		hence avoiding conflicts between commodity for this "physical place"
		
		Parameters
		----------
		topology : list
			list of disjoint set representing the relation (topology) between the nodes
		'''
		
		for set_constraints in topology:
			self.m.addConstrs(
				(self.flow.sum('*',i,j) <= 1 for i,j in set_constraints), "topo")

	def add_swapping_constraints(self,swapping_edges):
		'''
		addd constraint to avoid swapping of flows from one topology to another
		
		Parameters
		----------
		swapping_edges : list of set
			list of disjoint set, each set contains all the possible ways to go from cell1 to cell2 and vice-versa
		'''
		for set_constraints in swapping_edges:
			self.m.addConstrs(
				(self.flow.sum('*',i,j) <= 1 for i,j in set_constraints), "swap")


