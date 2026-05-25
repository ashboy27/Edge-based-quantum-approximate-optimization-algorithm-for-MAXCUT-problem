import networkx as nx


def pick_root(input_graph: nx.Graph) -> int:
    """
    Choose a root with high degree and good closeness centrality.
    """
    closeness_by_node = nx.closeness_centrality(input_graph)
    best_node = None
    best_score = None

    for node in input_graph.nodes():
        node_degree = input_graph.degree(node)
        node_closeness = closeness_by_node[node]
        score = (node_degree, node_closeness, -node)

        if best_score is None or score > best_score:
            best_score = score
            best_node = node

    if best_node is None:
        raise ValueError("Graph has no nodes to choose a root from.")

    return best_node


def build_star_tree(input_graph: nx.Graph) -> tuple[nx.Graph, int]:
    """
    Make a star tree rooted at a central vertex.
    Vertex with highest degree is choosen as central vertex
    All other vertices are connected to the central vertex in the tree, even if the edge does not exist in the original graph.
    This type of tree is used in the base paper.
    """
    central_root_node = pick_root(input_graph)

    star_tree = nx.Graph()

    star_tree.add_nodes_from(input_graph.nodes())
    for node in input_graph.nodes():
        if node != central_root_node:
            star_tree.add_edge(central_root_node, node)
    return star_tree, central_root_node


def build_greedy_heuristic_spanning_tree(input_graph: nx.Graph) -> tuple[nx.Graph, int]:
    """
    Our contribution
    """
    root_node = pick_root(input_graph)
    heuristic_spanning_tree = nx.Graph()
    heuristic_spanning_tree.add_nodes_from(input_graph.nodes())

    visited_nodes: set[int] = set()
    visited_nodes.add(root_node)

    node_depths: dict[int, int] = {}
    node_depths[root_node] = 0

    neighbor_sets: dict[int, set[int]] = {}
    for node in input_graph.nodes():
        neighbor_sets[node] = set()
        for neighbor_node in input_graph.neighbors(node):
            neighbor_sets[node].add(neighbor_node)

    while len(visited_nodes) < input_graph.number_of_nodes():
        best_candidate = None
        best_candidate_score = None
        best_parent_node = None
        best_child_node = None

        for current_node in list(visited_nodes):
            for candidate_node in neighbor_sets[current_node]:
                if candidate_node in visited_nodes:
                    continue

                shared_neighbors = set()
                for neighbor_node in neighbor_sets[current_node]:
                    if neighbor_node in neighbor_sets[candidate_node]:
                        shared_neighbors.add(neighbor_node)

                candidate_degree = input_graph.degree(candidate_node)
                current_depth = node_depths[current_node]

                score = 3.0 * candidate_degree
                score += len(shared_neighbors)
                score -= 0.4 * current_depth

                if best_candidate_score is None or score > best_candidate_score:
                    best_candidate_score = score
                    best_parent_node = current_node
                    best_child_node = candidate_node
                    best_candidate = (best_candidate_score, best_parent_node, best_child_node)

        if best_candidate is None:
            raise ValueError("Failed to build spanning tree. Check graph connectivity.")

        parent_node = best_parent_node
        child_node = best_child_node
        heuristic_spanning_tree.add_edge(parent_node, child_node)
        visited_nodes.add(child_node)
        node_depths[child_node] = node_depths[parent_node] + 1

    return heuristic_spanning_tree, root_node
