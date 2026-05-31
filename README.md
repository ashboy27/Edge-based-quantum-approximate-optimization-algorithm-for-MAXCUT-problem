# Topology-Aware Spanning Tree Initialization for the Edge-Based Quantum Approximate Optimization Algorithm 

https://github.com/user-attachments/assets/07d7d29c-e4b2-4b39-9af0-ec9383a70865
## Description

This project provides an interactive web app to test out the differences between a star-shape initialization and a topology aware initialization for spanning trees to approximate [MAX-CUT](https://www.cs.cmu.edu/afs/cs/academic/class/15854-f05/www/scribe/lec02.pdf). The repository contains our research paper which describes experiements and results in further detail.

The UI lets you draw or paste graphs, then compares star and heuristic spanning-tree strategies with circuit metrics and sampling results.

[Read more on the base problem](https://link.springer.com/article/10.1007/s11128-025-04925-0) and [our improvement](https://github.com/ashboy27/Edge-based-quantum-approximate-optimization-algorithm-for-MAXCUT-problem/blob/main/our_research_paper.pdf).

## Installation

### Docker
#### Prerequisites
- Docker Engine(Docker Desktop for Windows)
#### Build the Image
```bash
docker build -t qaoa-maxcut 
```

#### Run the Container
```bash
docker run -d --rm -p 8000:8000 qaoa-maxcut
```

Open http://localhost:8000 in your browser.
### Running Without Docker
#### Prerequisites
- Python 3.10+ (3.11 recommended)

#### Setup
```bash
git clone https://github.com/ashboy27/Edge-based-quantum-approximate-optimization-algorithm-for-MAXCUT-problem.git
cd Edge-based-quantum-approximate-optimization-algorithm-for-MAXCUT-problem
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

#### Start the Server
```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

Open http://localhost:8000 in your browser.




## Features

- Draw or paste graph edges in the browser
- Compare star vs heuristic spanning trees
- Run QAOA with configurable depth, shots, and iterations
- View circuit depth, gate count, CNOT cost, and histograms

