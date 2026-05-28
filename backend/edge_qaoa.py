import numpy as np
import networkx as nx
from collections import deque
from scipy.optimize import minimize

from qiskit import transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

from .utils import (
    build_qaoa_circuit,
    cut_value_from_vertex_labels,
    path_qubits,
    tree_edge_index,
)


def bits_to_vertex_labels(
    edge_bitstring: list[int],
    spanning_tree: nx.Graph,
    root_node: int,
) -> dict[int, int]:
    """
    Convert edge-bitstring on the tree into vertex labels.
    This is the 'edge -> vertex' reconstruction mentioned in the paper.
    """
    tree_edge_index_map = tree_edge_index(spanning_tree)
    vertex_labels: dict[int, int] = {root_node: 0}
    parent_by_node: dict[int, int | None] = {root_node: None}
    node_queue = deque([root_node])

    while node_queue:
        current_node = node_queue.popleft()
        for neighbor_node in spanning_tree.neighbors(current_node):
            if neighbor_node in parent_by_node:
                continue
            parent_by_node[neighbor_node] = current_node
            tree_edge_key = frozenset((current_node, neighbor_node))
            edge_index = tree_edge_index_map[tree_edge_key]
            vertex_labels[neighbor_node] = vertex_labels[current_node] ^ edge_bitstring[edge_index]
            node_queue.append(neighbor_node)

    return vertex_labels


def expected_cut_value(
    parameter_vector: np.ndarray,
    input_graph: nx.Graph,
    spanning_tree: nx.Graph,
    root_node: int,
    qaoa_depth: int,
) -> float:
    """
    Exact expectation from statevector simulation.
    This is the classical simulator version of the quantum circuit.
    """
    # Build the circuit for these parameters and get the exact statevector.
    quantum_circuit = build_qaoa_circuit(
        input_graph,
        spanning_tree,
        qaoa_depth,
        parameter_vector,
    )
    statevector = Statevector.from_instruction(quantum_circuit)
    probabilities = statevector.probabilities()

    number_of_qubits = spanning_tree.number_of_edges()
    expected_value = 0.0

    for basis_index in range(len(probabilities)):
        probability = probabilities[basis_index]
        if probability == 0.0:
            continue

        bits: list[int] = []
        for bit_position in range(number_of_qubits):
            bit_value = (basis_index >> bit_position) & 1
            bits.append(bit_value)

        vertex_labels = bits_to_vertex_labels(bits, spanning_tree, root_node)
        cut_value = cut_value_from_vertex_labels(input_graph, vertex_labels)
        expected_value += probability * cut_value

    return expected_value


def optimize_qaoa(
    input_graph: nx.Graph,
    spanning_tree: nx.Graph,
    root_node: int,
    qaoa_depth: int = 2,
    maximum_iterations: int = 80,
):
    """
    This function runs the classical optimization loop to find good QAOA parameters
    """

    initial_parameters: list[float] = []

    for layer_index in range(qaoa_depth):
        initial_parameters.append(0.7)
    for layer_index in range(qaoa_depth):
        initial_parameters.append(0.7)
    #If we have p layers, we will have 1 gamma and 1 beta per layer, so 2*p parameters in total
    initial_param_vector = np.array(initial_parameters, dtype=float)

    def objective_function(parameter_vector: np.ndarray) -> float:
        # We negate the expected cut because COBYLA minimizes.
        expected_value = expected_cut_value(
            parameter_vector,
            input_graph,
            spanning_tree,
            root_node,
            qaoa_depth,
        )
        return -expected_value

    optimizer_options = {
        "maxiter": maximum_iterations,
        "tol": 1e-3,
        "disp": False,
    }

    optimization_result = minimize(
        objective_function,
        initial_param_vector,
        method="COBYLA",
        options=optimizer_options,
    )
    return optimization_result


def sample_solution(
    parameter_vector: np.ndarray,
    input_graph: nx.Graph,
    spanning_tree: nx.Graph,
    root_node: int,
    qaoa_depth: int,
    shots: int = 4096,
):
    """
    Measure state and run for many iterations to get a distribution of bitstrings.
    """
    circuit = build_qaoa_circuit(input_graph, spanning_tree, qaoa_depth, parameter_vector)
    # Add measurement operations to every qubit.
    circuit.measure_all()

    simulator_backend = AerSimulator()
    transpiled_circuit = transpile(circuit, simulator_backend, optimization_level=3)

    execution_job = simulator_backend.run(transpiled_circuit, shots=shots)
    execution_result = execution_job.result()
    bitstring_counts = execution_result.get_counts()

    # Pick the most frequent measurement outcome.
    best_bitstring = None
    best_count = None
    for bitstring, count in bitstring_counts.items():
        if best_count is None or count > best_count:
            best_bitstring = bitstring
            best_count = count

    bits: list[int] = []
    for c in best_bitstring[::-1]:
        bits.append(int(c))

    vertex_labels = bits_to_vertex_labels(bits, spanning_tree, root_node)
    cut_value = cut_value_from_vertex_labels(input_graph, vertex_labels)

    return bitstring_counts, best_bitstring, vertex_labels, cut_value, transpiled_circuit


def estimated_cnot_per_layer(input_graph: nx.Graph, spanning_tree: nx.Graph) -> int:
    """
    This calculation is mentioned in paper
    """
    tree_edge_index_map = tree_edge_index(spanning_tree)
    total_cnot_estimate = 0
    for node_u, node_v in input_graph.edges():
        path_length = len(path_qubits(node_u, node_v, spanning_tree, tree_edge_index_map))
        total_cnot_estimate += 2 * (path_length - 1)
    return total_cnot_estimate