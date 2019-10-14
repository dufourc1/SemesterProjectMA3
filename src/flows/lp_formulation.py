import gurobipy
import numpy as np
import networkx as nx

class LpInstance:

	def __init__(self, graph,numberOfCommodities):
		'''
		build the gurobipy models and add the constraints specified in self.add_constraints()
		
		Parameters
		----------
		graph : nx.Digraph
			graph on which to run the multicommodity flow problem
			should have source and sink annotated like "source_agent_1", "sink_agent_1" 
			should have edges with both weight and capacity

		numberOfCommodities : int
			number of commodities in that can be found if going through all the sources and sinks in the graph
		'''
		
		commodities = np.arange(0,numberOfCommodities)
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
		self.flow = m.addVars(self.commodities, self.arcs, obj = self.cost, name = 'flow')

		#add the constraint to the model
		self.add_constraints()


	
	def solve(self):
		'''
		solve the linear programming instance using gurobipy
		'''
		self.m.optimize()

	def show_results(self):
		'''
		print the result if an optimal solution was found
		'''
		if m.status == gurobipy.GRB.Status.OPTIMAL:
			solution = m.getAttr('x', flow)
			for h in self.commodities:
				print('\nOptimal flows for %s:' % h)
				for i,j in self.arcs:
					if solution[h,i,j] > 0:
						print('%s -> %s: %g' % (i, j, solution[h,i,j]))




	def add_constraints(self):
		'''
		add the constraints for the LP problem
		'''
		# Arc-capacity constraints
		m.addConstrs(
			(flow.sum('*',i,j) <= self.capacity[i,j] for i,j in self.arcs), "cap")

		# Equivalent version using Python looping
		# for i,j in arcs:
		#   m.addConstr(sum(flow[h,i,j] for h in commodities) <= capacity[i,j],
		#               "cap[%s,%s]" % (i, j))


		# Flow-conservation constraints
		m.addConstrs(
			(flow.sum(h,'*',j) + inflow[h,j] == flow.sum(h,j,'*')
			for h in self.commodities for j in self.nodes), "node")
		# Alternate version:
		# m.addConstrs(
		#   (quicksum(flow[h,i,j] for i,j in arcs.select('*',j)) + inflow[h,j] ==
		#     quicksum(flow[h,j,k] for j,k in arcs.select(j,'*'))
		#     for h in commodities for j in nodes), "node")

		raise NotImplementedError



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

		raise NotImplementedError

	def get_dict_cost_per_commodity_per_arc(self,graph):
		'''
		Cost for triplets commodity-source-destination
		if in the graph no commodity is assigned a specific weight, the weight is assumed to be 
		the same for all commodities
		
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

		raise NotImplementedError


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
		raise NotImplementedError



