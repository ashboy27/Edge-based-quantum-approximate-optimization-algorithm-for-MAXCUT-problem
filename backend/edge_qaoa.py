import numpy as np
import networkx as nx
from collections import deque
from scipy.optimize import minimize

from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

from .graph_utils import cut_value_from_vertex_labels
from .tree_heuristic import tree_edge_index, path_qubits


def apply_multi_z_phase(
    quantum_circuit: QuantumCircuit,
    qubit_path_indices: list[int],
    gamma_angle: float,
) -> None:
    """
    Implement the paper's path-based Z / ZZ / ZZZ ... phase term.

    Step 3 in the paper:
    - for each original edge (u,v), apply the Hamiltonian term based on path length
      in the assigned spanning tree Ge.

    Here:
    - length 1 => single RZ
    - length 2 => ZZ-type phase via 2 CNOTs + RZ + 2 CNOTs
    - length 3+ => general parity-encoding chain
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

    Paper step mapping:
    1) choose edge-assigned graph Ge (handled outside)
    2) prepare |+>^{⊗(n-1)}
    3) apply problem Hamiltonian HP and mixing Hamiltonian HM
    4) repeat for p layers
    """
    number_of_qubits = spanning_tree.number_of_edges()
    tree_edge_index_map = tree_edge_index(spanning_tree)
    beta_angles = parameter_vector[:qaoa_depth]
    gamma_angles = parameter_vector[qaoa_depth:]

    quantum_circuit = QuantumCircuit(number_of_qubits)

    # Paper step 2: prepare n-1 qubits in |+> state
    for qubit_index in range(number_of_qubits):
        quantum_circuit.h(qubit_index)

    # Paper step 4: repeat p levels
    for layer_index in range(qaoa_depth):
        gamma_angle = gamma_angles[layer_index]
        beta_angle = beta_angles[layer_index]

        # Paper step 3: problem Hamiltonian over all original graph edges
        for node_u, node_v in input_graph.edges():
            path_qubit_indices = path_qubits(node_u, node_v, spanning_tree, tree_edge_index_map)
            apply_multi_z_phase(quantum_circuit, path_qubit_indices, gamma_angle)

        # Paper step 3: mixing Hamiltonian
        for qubit_index in range(number_of_qubits):
            quantum_circuit.rx(2.0 * beta_angle, qubit_index)

    return quantum_circuit


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
    Paper step 5: measure the final state and compute a cut.
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
    Paper-style CNOT estimate:
    N(HP) = sum 2(l_jk - 1)
    """
    tree_edge_index_map = tree_edge_index(spanning_tree)
    total_cnot_estimate = 0
    for node_u, node_v in input_graph.edges():
        path_length = len(path_qubits(node_u, node_v, spanning_tree, tree_edge_index_map))
        total_cnot_estimate += 2 * (path_length - 1)
    return total_cnot_estimate