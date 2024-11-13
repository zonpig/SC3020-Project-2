# Code for the GUI (you may use any other GUI development toolkit as long as it is compatible with Python)

import matplotlib

matplotlib.use("Agg")  # Use a non-GUI backend suitable for multi-threaded environments
import matplotlib.pyplot as plt
import networkx as nx
import os
from networkx.drawing.nx_agraph import graphviz_layout
from flask import Flask
import time

app = Flask(__name__)


def build_graph(G, node, parent=None, edge_label=""):
    node_id = f"{node['Node Type']}_{G.number_of_nodes()}"
    buffer = sum(
        node.get(key, 0)
        for key in [
            "Shared Hit Blocks",
            "Shared Read Blocks",
            "Shared Dirtied Blocks",
            "Shared Written Blocks",
        ]
    )
    total_cost = node.get("Total Cost", "N/A")
    row_size = node.get("Actual Rows", "N/A")

    # Determine if the current node is a leaf node
    is_leaf = "Plans" not in node or len(node["Plans"]) == 0

    # Append the Relation Name for leaf nodes
    relation_name = node.get("Relation Name", "")
    if is_leaf and relation_name:
        label = (
            f"<{relation_name}>\nCost: {total_cost}\nBuffer: {buffer}\nRows: {row_size}"
        )
    else:
        label = f"Cost: {total_cost}\nBuffer: {buffer}\nRows: {row_size}"

    G.add_node(node_id, label=label, type=node["Node Type"])
    if parent:
        G.add_edge(parent, node_id)

    if not is_leaf:
        for child in node["Plans"]:
            build_graph(G, child, node_id)


def visualize_query_plan(plan):
    G = nx.DiGraph()
    build_graph(G, plan)
    pos = graphviz_layout(G, prog="dot")

    plt.figure(figsize=(15, 10))  # Adjust the figure size

    # Draw nodes with custom shape and style
    nx.draw_networkx_nodes(
        G, pos, node_shape="o", node_size=500, node_color="lightblue", alpha=0.7
    )

    # Draw edges
    nx.draw_networkx_edges(G, pos, arrows=True)

    # Draw labels for details
    details_labels = {node: G.nodes[node]["label"] for node in G.nodes}
    type_labels = {node: G.nodes[node]["type"] for node in G.nodes}

    # Adjust label positions if necessary
    label_pos = {node: (pos[node][0], pos[node][1] - 13) for node in G.nodes}
    type_label_pos = {node: (pos[node][0], pos[node][1] + 10) for node in G.nodes}

    nx.draw_networkx_labels(
        G, label_pos, details_labels, font_size=9, font_weight="bold"
    )
    nx.draw_networkx_labels(G, type_label_pos, type_labels, font_size=9)

    plt.axis("off")  # Turn off the axis
    plt.tight_layout()  # Adjust the layout
    fn = "query_plan_tree" + str(int(time.time())) + ".png"
    image_path = os.path.join(app.root_path, "static", fn)

    plt.savefig(image_path, format="png", bbox_inches="tight")
    plt.close()  # Ensure the plot is closed and memory is freed

    return fn