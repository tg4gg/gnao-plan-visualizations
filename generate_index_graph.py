#!/usr/bin/env python3
"""Render the plan structure defined in index_config.yaml as a directed graph."""
from __future__ import annotations

from pathlib import Path

import matplotlib
import networkx as nx
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


CONFIG_PATH = Path("index_config.yaml")
OUTPUT_PATH = Path("index_graph.png")


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    return yaml.safe_load(config_path.read_text())


def build_graph(config: dict) -> nx.DiGraph:
    """Build a directed graph based on the YAML configuration."""
    root_label = config.get("root", {}).get("label", "Index")
    graph = nx.DiGraph()
    graph.add_node(root_label, kind="root")

    for section in config.get("sections", []):
        section_label = section["label"]
        graph.add_node(section_label, kind=section.get("kind", "section"))
        parent = section.get("parent") or root_label
        graph.add_edge(parent, section_label)

        for task in section.get("tasks", []):
            task_label = task["label"]
            graph.add_node(task_label, kind="task")
            task_parent = task.get("parent") or section_label
            graph.add_edge(task_parent, task_label)

    return graph


def draw_graph(graph: nx.DiGraph, out_path: Path) -> None:
    """Render the graph to disk and report where it was saved."""
    kind_colors = {"root": "#F6C667", "section": "#4F81BD", "task": "#9BBB59"}
    pos = nx.spring_layout(graph, seed=42)

    plt.figure(figsize=(12, 9))
    for kind, color in kind_colors.items():
        nodes = [node for node in graph.nodes if graph.nodes[node].get("kind") == kind]
        if nodes:
            nx.draw_networkx_nodes(
                graph,
                pos,
                nodelist=nodes,
                node_color=color,
                node_size=2000,
                alpha=0.9,
                linewidths=1.5,
                edgecolors="#333333",
            )
    nx.draw_networkx_edges(graph, pos, arrowstyle="-|>", arrowsize=12, edge_color="#333333")
    nx.draw_networkx_labels(graph, pos, font_size=9, font_weight="bold")
    plt.title("GCS Plan Index Graph", fontsize=16)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    print(f"Graph saved to {out_path}")


def main() -> None:
    config = load_config(CONFIG_PATH)

    graph = build_graph(config)
    draw_graph(graph, OUTPUT_PATH)


if __name__ == "__main__":
    main()
