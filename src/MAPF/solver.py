'''
definition of the abstract class for the solver methods
'''

from abc import ABC, abstractmethod
from .shortest_paths import *
from .colision import *

class Solver(ABC):
	'''
	Abstract class for the MAPF (Multiple Agent PathFinding)
	'''


	def __init__(self):
		self.high_level = None
		self.low_level = None

	def solve(self,graph):
		raise NotimplementedError


class Shortest_Path_with_waiting(Solver):

	def __init__(self):
		self.name = 'Shortest Path with waiting'
		self.low_level = Dijkstra()
		self.high_level = BasicChecker()

