from pathlib import Path

from .graph_utils import load_graph
from .tree_heuristic import build_greedy_heuristic_spanning_tree, build_star_tree
from .edge_qaoa import optimize_qaoa, sample_solution, estimated_cnot_per_layer
from .benchmark_plots import benchmark_by_level, benchmark_by_density


def run_case(input_graph: object, mode: str = "heuristic", qaoa_depth: int = 2):
    # Paper step 1: choose Ge
    if mode == "heuristic":
        spanning_tree, root_node = build_greedy_heuristic_spanning_tree(input_graph)
    else:
        spanning_tree, root_node = build_star_tree(input_graph)

    print(f"\n=== {mode.upper()} INITIALIZATION ===")
    print("root:", root_node)
    print("tree edges:", list(spanning_tree.edges()))
    print("paper-style estimated CNOTs per layer:", estimated_cnot_per_layer(input_graph, spanning_tree))

    # Paper step 6: optimize angles
    optimization_result = optimize_qaoa(
        input_graph,
        spanning_tree,
        root_node,
        qaoa_depth=qaoa_depth,
        maximum_iterations=80,
    )
    print("best angles:", optimization_result.x)
    print("expected cut:", -optimization_result.fun)

    # Paper step 5: measure final state
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
        shots=4096,
    )
    print("most frequent bitstring:", most_frequent_bitstring)
    print("cut from that bitstring:", sampled_cut_value)
    print("vertex labels:", vertex_labels)
    print("circuit depth:", transpiled_circuit.depth())
    print("cx count:", transpiled_circuit.count_ops().get("cx", 0))

    top_outcomes = sorted(bitstring_counts.items(), key=lambda item: item[1], reverse=True)[:10]
    print("top outcomes:", top_outcomes)


def main():
    graph_path = Path(__file__).with_name("graph.txt")
    input_graph = load_graph(str(graph_path))
    print("nodes:", input_graph.number_of_nodes())
    print("edges:", input_graph.number_of_edges())

    # Your new idea
    run_case(input_graph, mode="heuristic", qaoa_depth=2)

    # Paper baseline for comparison
    run_case(input_graph, mode="star", qaoa_depth=2)
    benchmark_by_level(number_of_nodes=8, number_of_edges=11, maximum_qaoa_depth=3, number_of_seeds=5)
    benchmark_by_density(number_of_nodes=12, edge_list=[11, 14, 17, 20, 23], number_of_seeds=5)


if __name__ == "__main__":
    main()