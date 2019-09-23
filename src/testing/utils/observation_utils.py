import numpy as np


def max_lt(seq, val):
    """
    Return greatest item in seq for which item < val applies.
    None is returned if seq was empty or all items in seq were >= val.
    """
    max = 0
    idx = len(seq) - 1
    while idx >= 0:
        if seq[idx] < val and seq[idx] >= 0 and seq[idx] > max:
            max = seq[idx]
        idx -= 1
    return max


def min_gt(seq, val):
    """
    Return smallest item in seq for which item > val applies.
    None is returned if seq was empty or all items in seq were >= val.
    """
    min = np.inf
    idx = len(seq) - 1
    while idx >= 0:
        if seq[idx] >= val and seq[idx] < min:
            min = seq[idx]
        idx -= 1
    return min


def norm_obs_clip(obs, clip_min=-1, clip_max=1, fixed_radius=0, normalize_to_range=False):
    """
    This function returns the difference between min and max value of an observation
    :param obs: Observation that should be normalized
    :param clip_min: min value where observation will be clipped
    :param clip_max: max value where observation will be clipped
    :return: returnes normalized and clipped observatoin
    """
    if fixed_radius > 0:
        max_obs = fixed_radius
    else:
        max_obs = max(1, max_lt(obs, 1000)) + 1

    min_obs = 0  # min(max_obs, min_gt(obs, 0))
    if normalize_to_range:
        min_obs = min_gt(obs, 0)
    if min_obs > max_obs:
        min_obs = max_obs
    if max_obs == min_obs:
        return np.clip(np.array(obs) / max_obs, clip_min, clip_max)
    norm = np.abs(max_obs - min_obs)
    return np.clip((np.array(obs) - min_obs) / norm, clip_min, clip_max)


def split_tree(tree, num_features_per_node, current_depth=0):
    """
    Splits the tree observation into different sub groups that need the same normalization.
    This is necessary because the tree observation includes two different distance:
    1. Distance from the agent --> This is measured in cells from current agent location
    2. Distance to targer --> This is measured as distance from cell to agent target
    3. Binary data --> Contains information about presence of object --> No normalization necessary
    Number 1. will depend on the depth and size of the tree search
    Number 2. will depend on the size of the map and thus the max distance on the map
    Number 3. Is independent of tree depth and map size and thus must be handled differently
    Therefore we split the tree into these two classes for better normalization.
    :param tree: Tree that needs to be split
    :param num_features_per_node: Features per node ATTENTION! this parameter is vital to correct splitting of the tree.
    :param current_depth: Keeping track of the current depth in the tree
    :return: Returns the three different groups of distance and binary values.
    """
    if len(tree) < num_features_per_node:
        return [], [], []

    depth = 0
    tmp = len(tree) / num_features_per_node - 1
    pow4 = 4
    while tmp > 0:
        tmp -= pow4
        depth += 1
        pow4 *= 4
    child_size = (len(tree) - num_features_per_node) // 4
    """
    Here we split the node features into the different classes of distances and binary values.
    Pay close attention to this part if you modify any of the features in the tree observation.
    """
    tree_data = tree[:6].tolist()
    distance_data = [tree[6]]
    agent_data = tree[7:num_features_per_node].tolist()
    # Split each child of the current node and continue to next depth level
    for children in range(4):
        child_tree = tree[(num_features_per_node + children * child_size):
                          (num_features_per_node + (children + 1) * child_size)]
        tmp_tree_data, tmp_distance_data, tmp_agent_data = split_tree(child_tree, num_features_per_node,
                                                                      current_depth=current_depth + 1)
        if len(tmp_tree_data) > 0:
            tree_data.extend(tmp_tree_data)
            distance_data.extend(tmp_distance_data)
            agent_data.extend(tmp_agent_data)

    return tree_data, distance_data, agent_data


def normalize_observation(observation, num_features_per_node=11, observation_radius=0):
    data, distance, agent_data = split_tree(tree=np.array(observation), num_features_per_node=num_features_per_node,
                                            current_depth=0)
    data = norm_obs_clip(data, fixed_radius=observation_radius)
    distance = norm_obs_clip(distance, normalize_to_range=True)
    agent_data = np.clip(agent_data, -1, 1)
    normalized_obs = np.concatenate((np.concatenate((data, distance)), agent_data))
    return normalized_obs
