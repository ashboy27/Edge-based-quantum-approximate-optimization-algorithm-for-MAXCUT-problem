import networkx as nx


def load_graph(graph_file_path: str) -> nx.Graph:
    """
    Load an unweighted or weighted graph from a text file.

    Format:
        first line: n m
        next lines: u v [w]

    If the file does not exist, return a small default connected graph.
    """
    try:
        with open(graph_file_path, "r", encoding="utf-8") as graph_file_handle:
            first_line_tokens = graph_file_handle.readline().split()
            if len(first_line_tokens) < 2:
                raise ValueError("First line must contain: n m")

            number_of_nodes = int(first_line_tokens[0])
            graph_instance = nx.Graph()
            graph_instance.add_nodes_from(range(number_of_nodes))

            for line in graph_file_handle:
                stripped_line = line.strip()
                if not stripped_line:
                    continue
                line_tokens = stripped_line.split()
                source_node = int(line_tokens[0])
                target_node = int(line_tokens[1])
                edge_weight = float(line_tokens[2]) if len(line_tokens) >= 3 else 1.0
                graph_instance.add_edge(source_node, target_node, weight=edge_weight)

        if not nx.is_connected(graph_instance):
            raise ValueError("Graph must be connected.")
        return graph_instance

    except FileNotFoundError:
        graph_instance = nx.Graph()
        graph_instance.add_nodes_from(range(6))
        graph_instance.add_edges_from([
            (0, 1), (1, 2), (2, 3), (3, 4), (4, 5),
            (0, 2), (1, 3), (2, 4)
        ])
        return graph_instance


def cut_value_from_vertex_labels(
    input_graph: nx.Graph,
    vertex_labels: dict[int, int],
) -> float:
    """
    Compute MAX-CUT value from vertex labels 0/1.
    """
    cut_value = 0.0
    for node_u, node_v, edge_data in input_graph.edges(data=True):
        edge_weight = edge_data.get("weight", 1.0)
        if vertex_labels[node_u] != vertex_labels[node_v]:
            cut_value += edge_weight
    return cut_value