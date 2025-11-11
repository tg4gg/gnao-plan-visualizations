#!/usr/bin/env python3
"""Generate multiple visualizations for the GCS plan tasks."""
from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
from typing import Iterable

import yaml

import matplotlib
import networkx as nx
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import colors as mcolors  # noqa: E402
from matplotlib import colormaps  # noqa: E402
from matplotlib import patches  # noqa: E402
from matplotlib_venn import venn3  # noqa: E402

CONFIG_PATH = Path("index_config.yaml")
OUTPUTS = {
    "venn": Path("tasks_venn.png"),
    "venn_detailed": Path("tasks_venn_detailed.png"),
    "venn_detailed_no_pct": Path("tasks_venn_detailed_no_pct.png"),
    "bars": Path("category_combinations_bar.png"),
    "network": Path("category_task_network.png"),
    "heatmap": Path("category_task_heatmap.png"),
}

DEFAULT_CATEGORIES = ["Science", "Systems Engineering", "Software"]


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    return yaml.safe_load(config_path.read_text())


def extract_tasks(config: dict) -> list[dict[str, object]]:
    tasks: list[dict[str, object]] = []
    for section in config.get("sections", []):
        section_categories = set(section.get("categories", []))
        for task in section.get("tasks", []):
            task_categories = set(task.get("categories", [])) or section_categories
            completion = int(task.get("completion", section.get("completion", 0)) or 0)
            completion = max(0, min(100, completion))
            blocker = bool(task.get("blocker", section.get("blocker", False)))
            tasks.append({
                "name": task["label"],
                "categories": task_categories,
                "parent_section": section["label"],
                "completion": completion,
                "blocker": blocker,
            })
    if not tasks:
        raise ValueError("No tasks defined in the configuration.")
    return tasks


def build_category_sets(tasks: Iterable[dict[str, object]], category_order: list[str]) -> dict[str, set[str]]:
    """Return mapping of category -> task names."""
    category_sets: dict[str, set[str]] = {cat: set() for cat in category_order}
    for task in tasks:
        for category in task["categories"]:
            category_sets[category].add(str(task["name"]))
    return category_sets


def draw_venn(category_sets: dict[str, set[str]], category_order: list[str]) -> None:
    plt.figure(figsize=(8, 6))
    venn3(
        subsets=(
            category_sets[category_order[0]],
            category_sets[category_order[1]],
            category_sets[category_order[2]],
        ),
        set_labels=category_order,
    )
    plt.title("Task Overlaps by Discipline")
    plt.tight_layout()
    plt.savefig(OUTPUTS["venn"], dpi=300)
    plt.close()


def completion_to_color(percent: int) -> str:
    """Map a completion percentage to a hex color."""
    normalized = max(0, min(100, percent)) / 100
    cmap = colormaps["Greens"]
    rgba = cmap(0.3 + 0.7 * normalized)
    return mcolors.to_hex(rgba)


def draw_venn_detailed(
    category_sets: dict[str, set[str]],
    tasks: list[dict[str, object]],
    category_order: list[str],
    show_percentage: bool = True,
    output_path: Path | None = None,
    title_suffix: str = "",
) -> None:
    plt.figure(figsize=(10, 8))
    venn = venn3(
        subsets=(
            category_sets[category_order[0]],
            category_sets[category_order[1]],
            category_sets[category_order[2]],
        ),
        set_labels=category_order,
    )
    region_map = {key: [] for key in ["100", "010", "001", "110", "101", "011", "111"]}
    for task in tasks:
        region_key = "".join("1" if cat in task["categories"] else "0" for cat in category_order)
        if region_key.count("1") == 0:
            continue
        region_map.setdefault(region_key, []).append(task)

    ax = plt.gca()

    pending_progress: list[tuple[plt.Text, int]] = []

    for region_id, task_list in region_map.items():
        label = venn.get_label_by_id(region_id)
        if label is None:
            continue
        center = label.get_position()
        label.set_text("")
        if not task_list:
            continue
        cols = 1 if len(task_list) <= 6 else 2
        rows = math.ceil(len(task_list) / cols)
        dx = 0.12 / cols if cols > 1 else 0
        dy = 0.065
        start_x = center[0] - (cols - 1) * dx / 2
        start_y = center[1] + (rows - 1) * dy / 2
        for idx, task in enumerate(task_list):
            row = idx // cols
            col = idx % cols
            x = start_x + col * dx
            y = start_y - row * dy
            completion = int(task.get("completion", 0))
            blocker = bool(task.get("blocker", False))
            text = f"{task['name']} ({completion}%)" if show_percentage else task["name"]
            base_color = "#F8D7DA" if blocker else "none"
            base_alpha = 0.95 if blocker else 1.0
            text_obj = plt.text(
                x,
                y,
                text,
                ha="center",
                va="center",
                fontsize=8,
                bbox={
                    "boxstyle": "round,pad=0.25",
                    "facecolor": base_color,
                    "edgecolor": "#444444",
                    "linewidth": 0.8,
                    "alpha": base_alpha,
                },
                zorder=3,
            )
            bbox_patch = text_obj.get_bbox_patch()
            bbox_patch.set_zorder(2)
            if not blocker and completion > 0:
                pending_progress.append((text_obj, completion))

    fig = plt.gcf()
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    for text_obj, completion in pending_progress:
        bbox_patch = text_obj.get_bbox_patch()
        bbox_disp = bbox_patch.get_window_extent(renderer=renderer)
        (x0, y0) = inv.transform((bbox_disp.x0, bbox_disp.y0))
        (x1, y1) = inv.transform((bbox_disp.x1, bbox_disp.y1))
        width = x1 - x0
        height = y1 - y0
        progress_width = width * (completion / 100)
        progress = patches.Rectangle(
            (x0, y0),
            progress_width,
            height,
            linewidth=0,
            facecolor=completion_to_color(completion),
            alpha=0.85,
            zorder=2.5,
            transform=ax.transData,
        )
        progress.set_clip_path(bbox_patch)
        ax.add_patch(progress)
    title = "Task Overlaps by Discipline (detailed)"
    if title_suffix:
        title = f"{title} {title_suffix}"
    plt.title(title)
    plt.tight_layout()
    out_path = output_path or OUTPUTS["venn_detailed"]
    plt.savefig(out_path, dpi=300)
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


def draw_network(tasks: list[dict[str, object]], category_order: list[str]) -> None:
    graph = nx.Graph()
    graph.add_nodes_from(category_order, kind="category")
    for task in tasks:
        name = str(task["name"])
        graph.add_node(name, kind="task")
        for category in task["categories"]:
            graph.add_edge(category, name)

    pos = nx.bipartite_layout(graph, category_order)
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


def draw_heatmap(tasks: list[dict[str, object]], category_order: list[str]) -> None:
    task_names = [task["name"] for task in tasks]
    matrix = np.array(
        [[1 if category in task["categories"] else 0 for category in category_order] for task in tasks]
    )
    cmap = mcolors.ListedColormap(["#D9E1F2", "#4472C4"])

    height = max(4, len(task_names) * 0.4)
    plt.figure(figsize=(8, height))
    plt.imshow(matrix, aspect="auto", cmap=cmap)
    plt.colorbar(label="Membership", ticks=[0, 1])
    plt.xticks(range(len(category_order)), category_order, rotation=20, ha="right")
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
    config = load_config(CONFIG_PATH)
    category_order = config.get("categories") or DEFAULT_CATEGORIES
    if len(category_order) != 3:
        raise ValueError("Venn diagrams require exactly three categories.")

    tasks = extract_tasks(config)
    category_sets = build_category_sets(tasks, category_order)

    draw_venn(category_sets, category_order)
    draw_venn_detailed(category_sets, tasks, category_order)
    draw_venn_detailed(
        category_sets,
        tasks,
        category_order,
        show_percentage=False,
        output_path=OUTPUTS["venn_detailed_no_pct"],
        title_suffix="(names only)",
    )
    draw_bar_chart(tasks)
    draw_network(tasks, category_order)
    draw_heatmap(tasks, category_order)

    print("Generated diagrams:")
    for key, path in OUTPUTS.items():
        print(f"- {key}: {path}")


if __name__ == "__main__":
    main()
