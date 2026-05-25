import random
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt

from .tree_heuristic import build_greedy_heuristic_spanning_tree, build_star_tree
from .edge_qaoa import optimize_qaoa, sample_solution, estimated_cnot_per_layer


def random_connected_graph(
    number_of_nodes: int,
    number_of_edges: int,
    random_seed: int | None = None,
):
    """
    Generate a connected random graph with n nodes and m edges.
    Similar spirit to the random graph experiments in the paper.
    """
    if random_seed is not None:
        random.seed(random_seed)
        np.random.seed(random_seed)

    if number_of_edges < number_of_nodes - 1:
        raise ValueError("Need at least n-1 edges for a connected graph.")

    graph_instance = nx.Graph()
    graph_instance.add_nodes_from(range(number_of_nodes))

    # first make a random spanning tree
    node_list = list(range(number_of_nodes))
    random.shuffle(node_list)
    for node_index in range(1, number_of_nodes):
        source_node = node_list[node_index]
        target_node = node_list[random.randrange(0, node_index)]
        graph_instance.add_edge(source_node, target_node, weight=1.0)

    # add remaining edges
    possible_edges: list[tuple[int, int]] = []
    for node_i in range(number_of_nodes):
        for node_j in range(node_i + 1, number_of_nodes):
            if not graph_instance.has_edge(node_i, node_j):
                possible_edges.append((node_i, node_j))
    random.shuffle(possible_edges)

    remaining_edge_count = max(0, number_of_edges - (number_of_nodes - 1))
    for source_node, target_node in possible_edges[:remaining_edge_count]:
        graph_instance.add_edge(source_node, target_node, weight=1.0)

    return graph_instance


def run_single_graph(
    input_graph: nx.Graph,
    mode: str = "heuristic",
    maximum_qaoa_depth: int = 3,
):
    """
    Run QAOA on one graph and return metrics for all p values from 1..p.
    """
    if mode == "heuristic":
        spanning_tree, root_node = build_greedy_heuristic_spanning_tree(input_graph)
    else:
        spanning_tree, root_node = build_star_tree(input_graph)

    approximation_ratios: list[float] = []
    circuit_depths: list[int] = []
    cnot_counts: list[int] = []

    for qaoa_depth in range(1, maximum_qaoa_depth + 1):
        optimization_result = optimize_qaoa(
            input_graph,
            spanning_tree,
            root_node,
            qaoa_depth=qaoa_depth,
            maximum_iterations=60,
        )
        (
            bitstring_counts,
            most_frequent_bitstring,
            vertex_labels,
            sampled_cut_value,
            transpiled_circuit,
        ) = sample_solution(
            optimization_result.x,
            input_graph,
            spanning_tree,
            root_node,
            qaoa_depth=qaoa_depth,
            shots=2048,
        )

        # approximate ratio proxy:
        # use sampled cut / maximum possible cut from brute force for small graphs
        # for benchmarking, this is enough for small-to-medium graphs
        maximum_cut_value = brute_force_max_cut(input_graph)
        ratio = sampled_cut_value / maximum_cut_value if maximum_cut_value > 0 else 0.0

        approximation_ratios.append(ratio)
        circuit_depths.append(transpiled_circuit.depth())
        cnot_counts.append(transpiled_circuit.count_ops().get("cx", 0))

    return np.array(approximation_ratios), np.array(circuit_depths), np.array(cnot_counts)


def brute_force_max_cut(input_graph: nx.Graph) -> float:
    """
    Exact max-cut for small graphs only.
    """
    number_of_nodes = input_graph.number_of_nodes()
    best_cut_value = 0.0
    for bitmask in range(1 << number_of_nodes):
        vertex_labels = {node_index: (bitmask >> node_index) & 1 for node_index in range(number_of_nodes)}
        current_cut_value = 0.0
        for node_u, node_v, edge_data in input_graph.edges(data=True):
            if vertex_labels[node_u] != vertex_labels[node_v]:
                current_cut_value += edge_data.get("weight", 1.0)
        if current_cut_value > best_cut_value:
            best_cut_value = current_cut_value
    return best_cut_value


def benchmark_by_level(
    number_of_nodes: int = 10,
    number_of_edges: int = 14,
    maximum_qaoa_depth: int = 3,
    number_of_seeds: int = 5,
):
    """
    Similar to the paper's approximation-ratio plots.
    """
    star_initialization_ratios = np.zeros(maximum_qaoa_depth)
    heuristic_initialization_ratios = np.zeros(maximum_qaoa_depth)

    for seed_index in range(number_of_seeds):
        graph_instance = random_connected_graph(number_of_nodes, number_of_edges, random_seed=seed_index)

        star_ratios, _, _ = run_single_graph(
            graph_instance,
            mode="star",
            maximum_qaoa_depth=maximum_qaoa_depth,
        )
        heuristic_ratios, _, _ = run_single_graph(
            graph_instance,
            mode="heuristic",
            maximum_qaoa_depth=maximum_qaoa_depth,
        )

        star_initialization_ratios += star_ratios
        heuristic_initialization_ratios += heuristic_ratios

    star_initialization_ratios /= number_of_seeds
    heuristic_initialization_ratios /= number_of_seeds

    depth_values = np.arange(1, maximum_qaoa_depth + 1)

    plt.figure(figsize=(8, 5))
    plt.plot(depth_values, star_initialization_ratios, marker="o", label="Star initialization")
    plt.plot(depth_values, heuristic_initialization_ratios, marker="o", label="Heuristic initialization")
    plt.xlabel("QAOA level p")
    plt.ylabel("Approximation ratio")
    plt.title("Approximation Ratio vs QAOA Level")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def benchmark_by_density(
    number_of_nodes: int = 20,
    edge_list: list[int] | None = None,
    number_of_seeds: int = 10,
):
    """
    Similar to the paper's depth/CNOT box-style density comparisons.
    """
    if edge_list is None:
        edge_list = [
            number_of_nodes - 1,
            number_of_nodes + 5,
            number_of_nodes + 10,
            number_of_nodes + 15,
            number_of_nodes + 20,
        ]

    star_depth_values: list[list[int]] = []
    heuristic_depth_values: list[list[int]] = []
    star_cnot_values: list[list[int]] = []
    heuristic_cnot_values: list[list[int]] = []

    for edge_count in edge_list:
        star_depth_samples: list[int] = []
        heuristic_depth_samples: list[int] = []
        star_cnot_samples: list[int] = []
        heuristic_cnot_samples: list[int] = []

        for seed_index in range(number_of_seeds):
            graph_instance = random_connected_graph(
                number_of_nodes,
                edge_count,
                random_seed=1000 + seed_index,
            )

            star_tree, star_root = build_star_tree(graph_instance)
            heuristic_tree, heuristic_root = build_greedy_heuristic_spanning_tree(graph_instance)

            fixed_qaoa_depth = 2
            star_result = optimize_qaoa(
                graph_instance,
                star_tree,
                star_root,
                qaoa_depth=fixed_qaoa_depth,
                maximum_iterations=40,
            )
            heuristic_result = optimize_qaoa(
                graph_instance,
                heuristic_tree,
                heuristic_root,
                qaoa_depth=fixed_qaoa_depth,
                maximum_iterations=40,
            )

            (
                star_bitstring_counts,
                star_most_frequent_bitstring,
                star_vertex_labels,
                star_sampled_cut_value,
                star_circuit,
            ) = sample_solution(
                star_result.x,
                graph_instance,
                star_tree,
                star_root,
                qaoa_depth=fixed_qaoa_depth,
                shots=512,
            )
            (
                heuristic_bitstring_counts,
                heuristic_most_frequent_bitstring,
                heuristic_vertex_labels,
                heuristic_sampled_cut_value,
                heuristic_circuit,
            ) = sample_solution(
                heuristic_result.x,
                graph_instance,
                heuristic_tree,
                heuristic_root,
                qaoa_depth=fixed_qaoa_depth,
                shots=512,
            )

            star_depth_samples.append(star_circuit.depth())
            heuristic_depth_samples.append(heuristic_circuit.depth())
            star_cnot_samples.append(star_circuit.count_ops().get("cx", 0))
            heuristic_cnot_samples.append(heuristic_circuit.count_ops().get("cx", 0))

        star_depth_values.append(star_depth_samples)
        heuristic_depth_values.append(heuristic_depth_samples)
        star_cnot_values.append(star_cnot_samples)
        heuristic_cnot_values.append(heuristic_cnot_samples)

    fig, axis_array = plt.subplots(1, 2, figsize=(12, 5))

    axis_array[0].boxplot(
        star_depth_values,
        positions=np.array(edge_list) - 0.2,
        widths=0.3,
    )
    axis_array[0].boxplot(
        heuristic_depth_values,
        positions=np.array(edge_list) + 0.2,
        widths=0.3,
    )
    axis_array[0].set_xlabel("Number of edges")
    axis_array[0].set_ylabel("Circuit depth")
    axis_array[0].set_title("Circuit Depth vs Graph Density")
    axis_array[0].legend(["Star", "Heuristic"], loc="best")

    axis_array[1].boxplot(
        star_cnot_values,
        positions=np.array(edge_list) - 0.2,
        widths=0.3,
    )
    axis_array[1].boxplot(
        heuristic_cnot_values,
        positions=np.array(edge_list) + 0.2,
        widths=0.3,
    )
    axis_array[1].set_xlabel("Number of edges")
    axis_array[1].set_ylabel("CNOT count")
    axis_array[1].set_title("CNOT Count vs Graph Density")
    axis_array[1].legend(["Star", "Heuristic"], loc="best")

    plt.tight_layout()
    plt.show()