from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .edge_qaoa import optimize_qaoa, sample_solution
from .graph_utils import cut_value_from_vertex_labels
from .tree_heuristic import build_greedy_heuristic_spanning_tree, build_star_tree


class EdgeInput(BaseModel):
    u: int
    v: int


class EvaluateRequest(BaseModel):
    nodeCount: int = Field(..., ge=2)
    edges: list[EdgeInput]
    zeroBased: bool = True
    pMax: int = Field(3, ge=1, le=5)
    shots: int = Field(1024, ge=128, le=8192)
    maxIter: int = Field(60, ge=10, le=300)


class ModeResult(BaseModel):
    mode: str
    root: int
    treeEdges: list[list[int]]
    approxRatios: list[float | None]
    sampledCuts: list[float]
    histogram: dict[str, int]


class EvaluateResponse(BaseModel):
    nodeCount: int
    edgeCount: int
    maxCut: float | None
    results: list[ModeResult]


app = FastAPI(title="Edge-Based QAOA Max-Cut")

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
def index() -> FileResponse:
    index_path = frontend_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found.")
    return FileResponse(str(index_path))


@app.get("/flutter_service_worker.js")
def flutter_service_worker() -> Response:
    return Response(status_code=204)


def build_graph(
    node_count: int,
    edge_list: list[EdgeInput],
    zero_based_indexing_enabled: bool,
) -> nx.Graph:
    nodes_in_graph = range(node_count)
    graph_built_from_user_input = nx.Graph()
    graph_built_from_user_input.add_nodes_from(nodes_in_graph)

    index_base_offset = 0 if zero_based_indexing_enabled else 1
    for edge in edge_list:
        source_node_index = edge.u - index_base_offset
        target_node_index = edge.v - index_base_offset
        if (
            source_node_index < 0
            or target_node_index < 0
            or source_node_index >= node_count
            or target_node_index >= node_count
        ):
            raise HTTPException(status_code=400, detail="Edge has invalid node index.")
        if source_node_index == target_node_index:
            raise HTTPException(status_code=400, detail="Self loops are not supported.")
        graph_built_from_user_input.add_edge(source_node_index, target_node_index, weight=1.0)

    if not nx.is_connected(graph_built_from_user_input):
        raise HTTPException(status_code=400, detail="Graph must be connected.")

    return graph_built_from_user_input


def brute_force_max_cut(graph_built_from_user_input_normalized: nx.Graph) -> float:
    number_of_nodes = graph_built_from_user_input_normalized.number_of_nodes()
    best_cut_value = 0.0
    for bitmask in range(1 << number_of_nodes):
        vertex_labels = {node_index: (bitmask >> node_index) & 1 for node_index in range(number_of_nodes)}
        current_cut_value = 0.0
        for node_u, node_v, edge_data in graph_built_from_user_input_normalized.edges(data=True):
            if vertex_labels[node_u] != vertex_labels[node_v]:
                current_cut_value += edge_data.get("weight", 1.0)
        if current_cut_value > best_cut_value:
            best_cut_value = current_cut_value
    return best_cut_value


def evaluate_mode(
    graph_built_from_user_input_normalized: nx.Graph,
    mode: str,
    maximum_qaoa_depth: int,
    number_of_shots: int,
    maximum_iterations_choosen_by_user: int,
    actual_max_cut_dervied_from_brute_force: float | None,
) -> ModeResult:
    if mode == "heuristic":
        spanning_tree, root_node = build_greedy_heuristic_spanning_tree(graph_built_from_user_input_normalized)
    else:
        spanning_tree, root_node = build_star_tree(graph_built_from_user_input_normalized)

    approximation_ratios: list[float | None] = []
    sampled_cut_values: list[float] = []
    histogram_by_bitstring: dict[str, int] = {}

    for qaoa_depth in range(1, maximum_qaoa_depth + 1):
        optimization_result = optimize_qaoa(
            graph_built_from_user_input_normalized,
            spanning_tree,
            root_node,
            qaoa_depth=qaoa_depth,
            maximum_iterations=maximum_iterations_choosen_by_user,
        )
        (
            bitstring_counts,
            most_frequent_bitstring,
            vertex_labels,
            sampled_cut_value,
            transpiled_circuit,
        ) = sample_solution(
            optimization_result.x,
            graph_built_from_user_input_normalized,
            spanning_tree,
            root_node,
            qaoa_depth=qaoa_depth,
            shots=number_of_shots,
        )
        if most_frequent_bitstring is None:
            raise ValueError("Sampling produced no bitstrings to evaluate.")
        if vertex_labels is None or transpiled_circuit is None:
            raise ValueError("Sampling output was incomplete.")
        sampled_cut_values.append(sampled_cut_value)

        if (
            actual_max_cut_dervied_from_brute_force is not None
            and actual_max_cut_dervied_from_brute_force > 0
        ):
            approximation_ratios.append(sampled_cut_value / actual_max_cut_dervied_from_brute_force)
        else:
            approximation_ratios.append(None)

        if qaoa_depth == maximum_qaoa_depth:
            histogram_by_bitstring = bitstring_counts

    return ModeResult(
        mode=mode,
        root=root_node,
        treeEdges=[[node_u, node_v] for node_u, node_v in spanning_tree.edges()],
        approxRatios=approximation_ratios,
        sampledCuts=sampled_cut_values,
        histogram=histogram_by_bitstring,
    )


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(request_payload: EvaluateRequest) -> EvaluateResponse:
    graph_built_from_user_input_normalized = build_graph(
        request_payload.nodeCount,
        request_payload.edges,
        request_payload.zeroBased,
    )
    actual_max_cut_dervied_from_brute_force = None
    if graph_built_from_user_input_normalized.number_of_nodes() <= 12:
        actual_max_cut_dervied_from_brute_force = brute_force_max_cut(graph_built_from_user_input_normalized)

    results = [
        evaluate_mode(
            graph_built_from_user_input_normalized,
            "star",
            request_payload.pMax,
            request_payload.shots,
            request_payload.maxIter,
            actual_max_cut_dervied_from_brute_force,
        ),
        evaluate_mode(
            graph_built_from_user_input_normalized,
            "heuristic",
            request_payload.pMax,
            request_payload.shots,
            request_payload.maxIter,
            actual_max_cut_dervied_from_brute_force,
        ),
    ]

    return EvaluateResponse(
        nodeCount=request_payload.nodeCount,
        edgeCount=graph_built_from_user_input_normalized.number_of_edges(),
        maxCut=actual_max_cut_dervied_from_brute_force,
        results=results,
    )
