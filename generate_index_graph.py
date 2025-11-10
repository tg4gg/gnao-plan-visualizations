#!/usr/bin/env python3
"""Parse the markdown index and render it as a directed graph."""
from __future__ import annotations

from pathlib import Path
import re

import matplotlib
import networkx as nx

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


MD_PATH = Path("GCS Plan to get to CDR.md")
OUTPUT_PATH = Path("index_graph.png")


def parse_index(md_path: Path) -> list[dict[str, str | bool]]:
    """Return a list of index entries from the markdown file."""
    text = md_path.read_text()
    lines = text.splitlines()
    entries: list[dict[str, str | bool]] = []
    capture = False

    for line in lines:
        if line.startswith("# Index"):
            capture = True
            continue
        if capture and line.startswith("#"):
            break
        stripped = line.strip()
        if not capture or not stripped or not stripped.startswith("["):
            continue
        match = re.search(r"\[(.*?)\]\(#(.*?)\)", stripped)
        if not match:
            continue
        raw_label = match.group(1)
        anchor = match.group(2)
        label = raw_label.replace("**", "").strip()
        label = re.sub(r"\s+\d+$", "", label).strip()
        is_section = "**" in raw_label
        entries.append({"label": label, "anchor": anchor, "is_section": is_section})

    return entries


def build_graph(entries: list[dict[str, str | bool]]) -> nx.DiGraph:
    """Build a directed graph where sections connect to their tasks."""
    graph = nx.DiGraph()
    root = "Index"
    graph.add_node(root, kind="root")
    current_section = root

    for entry in entries:
        label = str(entry["label"])
        kind = "section" if entry["is_section"] else "task"
        if label == root:
            current_section = root
            continue
        graph.add_node(label, kind=kind)
        if kind == "section":
            graph.add_edge(root, label)
            current_section = label
        else:
            parent = current_section if current_section else root
            graph.add_edge(parent, label)

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
    entries = parse_index(MD_PATH)
    if not entries:
        raise SystemExit("No index entries found in the markdown file")

    graph = build_graph(entries)
    draw_graph(graph, OUTPUT_PATH)


if __name__ == "__main__":
    main()
