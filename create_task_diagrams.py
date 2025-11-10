#!/usr/bin/env python3
"""Generate multiple visualizations for the GCS plan tasks."""
from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
from typing import Iterable
import re

import matplotlib
import networkx as nx
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import colors as mcolors  # noqa: E402
from matplotlib_venn import venn3  # noqa: E402

MD_PATH = Path("GCS Plan to get to CDR.md")
OUTPUTS = {
    "venn": Path("tasks_venn.png"),
    "venn_detailed": Path("tasks_venn_detailed.png"),
    "bars": Path("category_combinations_bar.png"),
    "network": Path("category_task_network.png"),
    "heatmap": Path("category_task_heatmap.png"),
}

CATEGORY_ORDER = ["Science", "Systems Engineering", "Software"]
SECTION_CATEGORY_MAP = {
    "Science Tasks": {"Science"},
    "Science + Systems Engineering Tasks": {"Science", "Systems Engineering"},
    "Systems Engineering Tasks": {"Systems Engineering"},
    "Systems Engineering + Software Tasks": {"Systems Engineering", "Software"},
    "Software Tasks": {"Software"},
}

HEADING_PATTERN = re.compile(r"^(#+)\s+(.*?)(?:\s+\{#.*\})?\s*$")


def clean_heading(text: str) -> str:
    """Normalize markdown heading text."""
    return text.replace("\\", "").strip()


def extract_tasks(md_path: Path) -> list[dict[str, object]]:
    """Parse the markdown and return tasks with their category assignments."""
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")

    tasks: list[dict[str, object]] = []
    current_section = None
    with md_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            match = HEADING_PATTERN.match(line)
            if not match:
                continue
            level = len(match.group(1))
            heading = clean_heading(match.group(2))
            if not heading:
                continue
            if level == 1:
                current_section = heading
            elif level == 2 and current_section in SECTION_CATEGORY_MAP:
                categories = SECTION_CATEGORY_MAP[current_section]
                tasks.append({
                    "name": heading,
                    "categories": set(categories),
                    "parent_section": current_section,
                })
    if not tasks:
        raise ValueError("No tasks extracted; check the markdown structure.")
    return tasks


def build_category_sets(tasks: Iterable[dict[str, object]]) -> dict[str, set[str]]:
    """Return mapping of category -> task names."""
    category_sets: dict[str, set[str]] = {cat: set() for cat in CATEGORY_ORDER}
    for task in tasks:
        for category in task["categories"]:
            category_sets[category].add(str(task["name"]))
    return category_sets


def draw_venn(category_sets: dict[str, set[str]]) -> None:
    plt.figure(figsize=(8, 6))
    venn3(
        subsets=(
            category_sets["Science"],
            category_sets["Systems Engineering"],
            category_sets["Software"],
        ),
        set_labels=CATEGORY_ORDER,
    )
    plt.title("Task Overlaps by Discipline")
    plt.tight_layout()
    plt.savefig(OUTPUTS["venn"], dpi=300)
    plt.close()


def draw_venn_detailed(category_sets: dict[str, set[str]]) -> None:
    plt.figure(figsize=(10, 8))
    venn = venn3(
        subsets=(
            category_sets["Science"],
            category_sets["Systems Engineering"],
            category_sets["Software"],
        ),
        set_labels=CATEGORY_ORDER,
    )
    science = category_sets["Science"]
    systems = category_sets["Systems Engineering"]
    software = category_sets["Software"]
    region_map = {
        "100": sorted(science - systems - software),
        "010": sorted(systems - science - software),
        "001": sorted(software - science - systems),
        "110": sorted((science & systems) - software),
        "101": sorted((science & software) - systems),
        "011": sorted((systems & software) - science),
        "111": sorted(science & systems & software),
    }
    for region_id, tasks in region_map.items():
        label = venn.get_label_by_id(region_id)
        if label is None:
            continue
        center = label.get_position()
        label.set_text("")
        if not tasks:
            continue
        cols = 1 if len(tasks) <= 6 else 2
        rows = math.ceil(len(tasks) / cols)
        dx = 0.12 / cols if cols > 1 else 0
        dy = 0.065
        start_x = center[0] - (cols - 1) * dx / 2
        start_y = center[1] + (rows - 1) * dy / 2
        for idx, task in enumerate(tasks):
            row = idx // cols
            col = idx % cols
            x = start_x + col * dx
            y = start_y - row * dy
            plt.text(
                x,
                y,
                task,
                ha="center",
                va="center",
                fontsize=8,
                bbox={
                    "boxstyle": "round,pad=0.25",
                    "facecolor": "#FFFFFF",
                    "edgecolor": "#444444",
                    "linewidth": 0.8,
                    "alpha": 0.85,
                },
            )
    plt.title("Task Overlaps by Discipline (detailed)")
    plt.tight_layout()
    plt.savefig(OUTPUTS["venn_detailed"], dpi=300)
    plt.close()


def draw_bar_chart(tasks: list[dict[str, object]]) -> None:
    combos = Counter(
        "+".join(sorted(task["categories"])) for task in tasks
    )
    labels = list(combos.keys())
    values = [combos[label] for label in labels]

    plt.figure(figsize=(8, 4))
    bars = plt.bar(labels, values, color="#4F81BD")
    plt.bar_label(bars, padding=3)
    plt.ylabel("Number of tasks")
    plt.title("Task counts by category combination")
    plt.tight_layout()
    plt.savefig(OUTPUTS["bars"], dpi=300)
    plt.close()


def draw_network(tasks: list[dict[str, object]]) -> None:
    graph = nx.Graph()
    graph.add_nodes_from(CATEGORY_ORDER, kind="category")
    for task in tasks:
        name = str(task["name"])
        graph.add_node(name, kind="task")
        for category in task["categories"]:
            graph.add_edge(category, name)

    pos = nx.bipartite_layout(graph, CATEGORY_ORDER)
    plt.figure(figsize=(12, 8))

    cat_nodes = [node for node, data in graph.nodes(data=True) if data["kind"] == "category"]
    task_nodes = [node for node, data in graph.nodes(data=True) if data["kind"] == "task"]

    nx.draw_networkx_nodes(
        graph,
        pos,
        nodelist=cat_nodes,
        node_color="#F6C667",
        node_size=2500,
        edgecolors="#333333",
        linewidths=1.5,
    )
    nx.draw_networkx_nodes(
        graph,
        pos,
        nodelist=task_nodes,
        node_color="#9BBB59",
        node_size=1600,
        edgecolors="#333333",
        linewidths=1.0,
    )
    nx.draw_networkx_labels(graph, pos, font_size=9, font_weight="bold")
    nx.draw_networkx_edges(graph, pos, width=1.5, edge_color="#666666")

    plt.title("Category-to-task relationships")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(OUTPUTS["network"], dpi=300)
    plt.close()


def draw_heatmap(tasks: list[dict[str, object]]) -> None:
    task_names = [task["name"] for task in tasks]
    matrix = np.array(
        [[1 if category in task["categories"] else 0 for category in CATEGORY_ORDER] for task in tasks]
    )
    cmap = mcolors.ListedColormap(["#D9E1F2", "#4472C4"])

    height = max(4, len(task_names) * 0.4)
    plt.figure(figsize=(8, height))
    plt.imshow(matrix, aspect="auto", cmap=cmap)
    plt.colorbar(label="Membership", ticks=[0, 1])
    plt.xticks(range(len(CATEGORY_ORDER)), CATEGORY_ORDER, rotation=20, ha="right")
    plt.yticks(range(len(task_names)), task_names)
    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            value = matrix[row, col]
            plt.text(col, row, str(value), ha="center", va="center", color="#000000")
    plt.title("Task membership heatmap")
    plt.tight_layout()
    plt.savefig(OUTPUTS["heatmap"], dpi=300)
    plt.close()


def main() -> None:
    tasks = extract_tasks(MD_PATH)
    category_sets = build_category_sets(tasks)

    draw_venn(category_sets)
    draw_venn_detailed(category_sets)
    draw_bar_chart(tasks)
    draw_network(tasks)
    draw_heatmap(tasks)

    print("Generated diagrams:")
    for key, path in OUTPUTS.items():
        print(f"- {key}: {path}")


if __name__ == "__main__":
    main()
