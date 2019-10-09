'''
methods to find the collisions in the paths
'''

import collections


class Collision:

	def __init__(self, time, list_agents, position):
		self.time = time
		self.agents = list_agents
		self.position = position


class BasicChecker:

	def __init__(self, *args, **kwargs):
	 super().__init__(*args, **kwargs)
	 self.name = 'basic collision checker'

	def check(self,paths):

		#get the longest length of the paths
		max_length = max([len(x) for x in paths])

		collisions = []

		#go trhough all the time steps
		for t in range(max_length):

			#get the cells occupied at time t
			cells_to_check = [x[t] for x in paths if t<len(x)]
			
			if cells_to_check >0:

				#check if there are collision
				set_cells = set(cells_to_check)
				if len(cells_to_check) != len(set_cells):
					
					#identification of the collisions
					for elt in set_cells:
						if cells_to_check.count(elt) > 1:
							collisions.append(Collision(t,[i for i in range()]))



