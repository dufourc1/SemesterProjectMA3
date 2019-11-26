import gurobipy


class MasterProblem:

	def __init__(self,initialSolution):
		self.model = gurobipy.Model("MasterProblem")
		self.columns = {}
		for i, path in initialSolution:
			self.columns[i] = path
		raise NotImplementedError()

	
	def build(self):
		self.generateVariables()
		self.generateConstraints()
		self.generateObjective()
		self.model.update()


	def generateVariables(self):

		raise NotImplementedError()

	def generateConstraints(self):
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
