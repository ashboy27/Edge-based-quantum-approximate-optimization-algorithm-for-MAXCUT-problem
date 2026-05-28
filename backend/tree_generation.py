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

def evaluate_cnot_cost(tree: nx.Graph, original_graph: nx.Graph) -> int:
    """
    Calculates the exact QAOA overhead: sum of 2*(l_jk - 1) 
    for all edges in the original graph.
    """
    # Precomputing all shortest paths in a tree is highly efficient
    path_lengths = dict(nx.all_pairs_shortest_path_length(tree))
    cost = 0
    
    for u, v in original_graph.edges():
        cost += 2 * (path_lengths[u][v] - 1)
        
    return cost

def build_greedy_heuristic_spanning_tree(input_graph: nx.Graph) -> tuple[nx.Graph, int]:
    """
    Our contribution
    """
    degrees = dict(input_graph.degree())
    root_node = max(degrees, key=degrees.get)
    current_tree = nx.bfs_tree(input_graph, root_node).to_undirected()
    current_cost = evaluate_cnot_cost(current_tree, input_graph)
    improved = True
    while improved:
        improved = False
        non_tree_edges = [e for e in input_graph.edges() if not current_tree.has_edge(*e)]
        
        for u, v in non_tree_edges:
            path = nx.shortest_path(current_tree, source=u, target=v)
            cycle_edges = [(path[i], path[i+1]) for i in range(len(path) - 1)]
            
            best_swap_out_edge = None
            best_cost = current_cost
            current_tree.add_edge(u, v)
            for cu, cv in cycle_edges:
                current_tree.remove_edge(cu, cv)
                new_cost = evaluate_cnot_cost(current_tree, input_graph)
                
                if new_cost < best_cost:
                    best_cost = new_cost
                    best_swap_out_edge = (cu, cv)
                    
                current_tree.add_edge(cu, cv)
            
            if best_swap_out_edge:
                current_tree.remove_edge(*best_swap_out_edge)
                current_cost = best_cost
                improved = True
                break 
            else:
                # Revert the temporary addition; this swap doesn't help
                current_tree.remove_edge(u, v)
                
    return current_tree, root_node