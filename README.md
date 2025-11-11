# GCS Plan Visualization

Tools for parsing the `GCS Plan to get to CDR.md` document and generating multiple visual summaries of the Science / Systems Engineering / Software workload. Task names and category mappings now live in `index_config.yaml`, so you can update the hierarchy without editing code.

## Contents
- `generate_index_graph.py`: Builds a directed graph from the markdown index to show the hierarchy of sections and tasks.
- `create_task_diagrams.py`: Extracts tasks per discipline and exports five diagrams (simple + detailed Venn, bar chart, bipartite network, heatmap).
- `design.txt`: High-level design notes covering parsing logic and visualization goals.
- `index_config.yaml`: Source of truth for sections, tasks, and category assignments.

## Requirements
- Python 3.11 (runs inside the existing `py3.11` conda environment).
- Packages: `matplotlib`, `matplotlib-venn`, `networkx`, `numpy`, `pyyaml` (install via `pip` in the environment if needed).

## Usage
```bash
# activate desired environment as needed
conda run -n py3.11 python create_task_diagrams.py
conda run -n py3.11 python generate_index_graph.py
```
Each script reads `index_config.yaml` (and, for context, `GCS Plan to get to CDR.md`) from the repo root and writes PNG files alongside the source. To rename tasks or adjust category assignments, edit `index_config.yaml` and rerun the scripts.

## Outputs
- `index_graph.png`: Hierarchical view derived from the markdown index.
- `tasks_venn.png`: Clean three-set Venn diagram.
- `tasks_venn_detailed.png`: Venn with task names rendered inside each overlap.
- `category_combinations_bar.png`: Category-combo counts.
- `category_task_network.png`: Bipartite category ↔ task graph.
- `category_task_heatmap.png`: Membership matrix.

Re-run the scripts whenever the markdown plan changes to refresh the visuals.
