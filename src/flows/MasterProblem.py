import gurobipy


class MasterProblem:

	def __init__(self,initialSolution, constraints,findConstraints):
		self.model = gurobipy.Model("MasterProblem")
		self.commodity = {}
		for i, path in initialSolution.items():
			self.commodity[i] = [path]

		self.constraints = constraints
		self.findConstraints_edges = findConstraints
		self.findConstraints_path, self.findPath_constraint = self.__Link_path_to_constraints()
	
	def build(self):
		self.generateVariables()
		self.generateConstraints()
		self.generateObjective()
		self.model.update()


	def generateVariables(self):
		#we add one variable per path for each commodity
		for commodity,paths in self.commodity.items():
			for i,path in enumerate(paths):
				self.pathVars = self.model.addVar(obj = len(path), vtype = gurobipy.GRB.INTEGER,name = f'path {i} for commodity {commodity}')


	def generateConstraints(self):
		for restriction in self.constraints:
			for path in self.findPath_constraint[restriction]:
				raise NotImplementedError()

	def generateObjective(self):
		raise NotImplementedError()



	def solveRelaxedModel(self):
		'''
		Relax the Master IP to an LP and solve it
		'''
		self.relaxedModel = self.model.relax()
		self.relaxedModel.optimize()


	def getDualVariables(self):
		'''
		return the dual values of the relaxation of the master LP
		'''
		return self.relaxedModel.getAttr("Pi", self.model.getConstrs())


	def addColumn(self):
		raise NotImplementedError()


	def __Link_path_to_constraints(self):
		'''
		Build a dict linking a path to the constraints it goes trough
		'''
		raise NotImplementedError()