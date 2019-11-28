import gurobipy
import numpy as np


class MasterProblem:
    '''
    Master problem (formulation (5.2.1) in report)

    Suppose at least one difference between s_k, s_i or t_k, t_i  if i is different than k
    '''

    def __init__(self, initialSolution, constraints, findConstraints,numberOfCommodities):
        '''
        create the necessary data structure to correctly handle the column generation procedure 
        
        Parameters
        ----------
        initialSolution : list
            list of initial solutions for each commodity (suppose that commodity k as solution initialSolution[k])

        constraints : list of sets

        findConstraints : dictionnary
            links each edge in the graph to the constraint it goes through

        numberOfCommodities : int        
        '''
        self.model = gurobipy.Model("MasterProblem")
        self.constraints = constraints
        self.findConstraints_edges = findConstraints
        self.commodities = np.arange(numberOfCommodities)
        self.__setup(initialSolution)


    def __setup(self,initialSolution):
        '''
        Builds all the necessary data structures for adding variables and constraints in an efficient way

        paths are uniquely identified as a tuple (commodity using it, index in this commodity)
        '''

        #list of all the paths (as list of edges used up now)
        self.pathVariables = [tuple(x) for x in initialSolution]
        

        # key (commodity, pathIndex), item : list of edges representing the path
        self.CommodityPath = {}
        #key is the path, item is the commodity that uses it and the index of the path wrt to this commodity
        self.PathCommodity = {}
        self.cost = {}
        for k in self.commodities:
            self.CommodityPath[(k,0)] = tuple(initialSolution[k])
            self.cost[(k,0)] = len(initialSolution[k])
            self.PathCommodity[tuple(initialSolution[k])] = (k,0)


        #list of activated constraints 
        self.constraintsActivated = set()
         #links constraints (as key) to a list of paths that go through them 
        self.findConstraints_path = {}
        #not optimal but once each problem --> to modify later if time 
        for path in self.pathVariables:
            for edge in path:
                if "source" not in edge[0] and "sink" not in edge[1]:
                    for c in self.findConstraints_edges[edge]:
                        self.constraintsActivated.add(frozenset(c))
                        if frozenset(c) in self.findConstraints_path.keys():
                            self.findConstraints_path[frozenset(c)].append(self.PathCommodity[tuple(path)])
                        else:
                            self.findConstraints_path[frozenset(c)] = [self.PathCommodity[tuple(path)]]
        
       

    def build(self):
        self.generateVariables()
        self.generateConstraints()
        self.generateObjective()
        self.model.update()

    def generateVariables(self):
        '''
        create the variables of the master problem, indexed as
         [
            commodity to which the path belongs, 
            path index in this commodity, 
            set of constraints it belongs to (hashed)
         ]
        '''
        # we add one variable per path for each commodity
        self.pathVars = self.model.addVars(self.CommodityPath, obj= self.cost, vtype = gurobipy.GRB.BINARY,name = "path")


    def generateConstraints(self):

        #add constraints to have exactly one unit per commodity 
        self.model.addConstrs((self.pathVars.sum(k,'*') == 1 for k in self.commodities), "unitFlow")

        #add constraints to respect the external restrictions
        # only iterate trough the constraints activated by the pathVariables we are currently using
        for i,constraint in enumerate(self.constraintsActivated):
            self.model.addConstr(
                (gurobipy.quicksum(self.pathVars[p] for p in self.findConstraints_path[constraint])<= 1),"Restrictions-"+str(i)
            )
     	


    def generateObjective(self):
        # objective is set by default to minimize in gurobi 
        # obj parameter in adVars did the job
        pass


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
        #update all the data structure produce in self.__setup()
        raise NotImplementedError()
        
        # below is the code from the webinar (as is) 
        #first the parameters given to the function
        objective = None
        newPattern = None # obtained using self.model.getAttr("X", self.model.getVars())  on the dual

        #then the actual code
        ctName = (f'PatternUseVar{len(self.model.getVars())}') 
        newColumn = gurobipy.Column(newPattern,self.model.getConstrs())
        self.model.addVar(vtype = gurobipy.GRB.INTEGER, lb = 0, obj = objective, column = newColumn, name = ctName)
        self.model.update()
        