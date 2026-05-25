import numpy as np
import networkx as nx
from qiskit import QuantumCircuit


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


def tree_edge_index(spanning_tree: nx.Graph) -> dict[frozenset, int]:
    """
    Map each tree edge to a qubit index.
    """
    tree_edge_index_map: dict[frozenset, int] = {}
    edge_counter = 0
    for node_u, node_v in spanning_tree.edges():
        tree_edge_index_map[frozenset((node_u, node_v))] = edge_counter
        edge_counter += 1
    return tree_edge_index_map


def path_qubits(
    start_node: int,
    end_node: int,
    spanning_tree: nx.Graph,
    tree_edge_index_map: dict[frozenset, int],
) -> list[int]:
    """
    Get qubit indices along the unique tree path between u and v.
    """
    shortest_path_nodes = nx.shortest_path(spanning_tree, start_node, end_node)
    qubit_indices: list[int] = []
    for path_index in range(len(shortest_path_nodes) - 1):
        node_a = shortest_path_nodes[path_index]
        node_b = shortest_path_nodes[path_index + 1]
        qubit_index = tree_edge_index_map[frozenset((node_a, node_b))]
        qubit_indices.append(qubit_index)
    return qubit_indices


def apply_multi_z_phase(
    quantum_circuit: QuantumCircuit,
    qubit_path_indices: list[int],
    gamma_angle: float,
) -> None:
    """
    Implement the path-based Z / ZZ / ZZZ ... phase term.
    """
    if len(qubit_path_indices) == 1:
        quantum_circuit.rz(-gamma_angle, qubit_path_indices[0])
        return

    for qubit_index in range(len(qubit_path_indices) - 1):
        quantum_circuit.cx(
            qubit_path_indices[qubit_index],
            qubit_path_indices[qubit_index + 1],
        )

    quantum_circuit.rz(-gamma_angle, qubit_path_indices[-1])

    for qubit_index in range(len(qubit_path_indices) - 2, -1, -1):
        quantum_circuit.cx(
            qubit_path_indices[qubit_index],
            qubit_path_indices[qubit_index + 1],
        )


def build_qaoa_circuit(
    input_graph: nx.Graph,
    spanning_tree: nx.Graph,
    qaoa_depth: int,
    parameter_vector: np.ndarray,
) -> QuantumCircuit:
    """
    Build the edge-based QAOA circuit.
    """
    number_of_qubits = spanning_tree.number_of_edges()
    tree_edge_index_map = tree_edge_index(spanning_tree)
    beta_angles = parameter_vector[:qaoa_depth]
    gamma_angles = parameter_vector[qaoa_depth:]

    quantum_circuit = QuantumCircuit(number_of_qubits)

    for qubit_index in range(number_of_qubits):
        quantum_circuit.h(qubit_index)

    for layer_index in range(qaoa_depth):
        gamma_angle = gamma_angles[layer_index]
        beta_angle = beta_angles[layer_index]

        for node_u, node_v in input_graph.edges():
            path_qubit_indices = path_qubits(node_u, node_v, spanning_tree, tree_edge_index_map)
            apply_multi_z_phase(quantum_circuit, path_qubit_indices, gamma_angle)

        for qubit_index in range(number_of_qubits):
            quantum_circuit.rx(2.0 * beta_angle, qubit_index)

    return quantum_circuit