import gurobipy
import numpy as np


class MasterProblem:
    '''
    Master problem (formulation (5.2.1) in report)

    Suppose at least one difference between s_k, s_i or t_k, t_i  if i is different than k
    '''

    def __init__(self, initialSolution, constraints, findConstraints,numberOfCommodities,verbose = False):
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
        if not verbose:
            gurobipy.setParam("LogToConsole",0)

        self.model = gurobipy.Model("MasterProblem")
        self.constraints = constraints
        self.findConstraints_edges = findConstraints
        self.commodities = np.arange(numberOfCommodities)
        self.__setup(initialSolution)
        self.indexes = {x:0 for x in self.commodities}
        self.stats = {
            "variablesAdded": [0 for x in self.commodities]
        }


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


        self.constraintsActivated = set()
         #links constraints (as key) to a list of paths that go through them 
        self.findConstraints_path = {}

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
            path index in this commodity
        ]
        '''
        # we add one variable per path for each commodity
        self.pathVars = self.model.addVars(self.CommodityPath, obj= self.cost, vtype = gurobipy.GRB.BINARY,name = "path")


    def generateConstraints(self):

        # add constraints to respect the external restrictions
        # only iterate trough the constraints activated by the pathVariables we are currently using
        for i,constraint in enumerate(self.constraintsActivated):
            self.model.addConstr(
                (gurobipy.quicksum(self.pathVars[p] for p in self.findConstraints_path[constraint])<= 1),"Restrictions-"+str(i)
            )

        #add constraints to have exactly one unit per commodity 
        self.model.addConstrs((self.pathVars.sum(k,'*') == 1 for k in self.commodities), "unitFlow")
     	


    def generateObjective(self):
        # objective is set by default to minimize in gurobi but set it anyway
        #  (1: minimize, -1: maximize)
        self.model.ModelSense = 1
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
        first are the values linked to the external restrictions (y_R)
        the last ones to the commodities (sigma_k)
        '''
        return self.relaxedModel.getAttr("Pi", self.model.getConstrs())


    def addColumn(self,pathToAdd):
        #update all the data structure produce in self.__setup()
        skipped = 0
        for commodity,path in pathToAdd.items():
            if path in self.pathVariables:
                print("skipped addition of path for commodity ",commodity)
                skipped += 1
            else:
                self.stats["variablesAdded"][commodity] += 1
                self.pathVariables.append(path)
                index = self.indexes[commodity] + 1
                self.indexes[commodity]+= 1
                self.CommodityPath[(commodity,index)] = path
                self.cost[(commodity,index)] = len(path)
                for edge in path:
                    if "source" not in edge[0] and "sink" not in edge[1]:
                        for c in self.findConstraints_edges[edge]:
                            self.constraintsActivated.add(frozenset(c))
                            if frozenset(c) in self.findConstraints_path.keys():
                                self.findConstraints_path[frozenset(c)].append((commodity,index))
                            else:
                                self.findConstraints_path[frozenset(c)] = [(commodity,index)]
        if skipped == len(list(pathToAdd.keys())):
            raise ValueError("only adding already added columns")
        self.model = gurobipy.Model("Master Problem")
        self.build()
    
    def get_solution(self):
        '''
        return the paths that are used in form of dictionnary indexed by commodity index
        path are represented as list of edges
        '''
        paths_to_get = {}
        for v in self.model.getVars():
            if v.x == 1:
                inter = v.VarName.split("[")[-1]
                inter = inter.split("]")[0]
                c = int(inter.split(",")[0])
                path = int(inter.split(",")[-1])
                paths_to_get[c] = self.CommodityPath[(c,path)]

        return paths_to_get
        