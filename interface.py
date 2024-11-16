import datetime
import json
import re

import dash_bootstrap_components as dbc
import networkx as nx
import plotly.graph_objects as go
from bs4 import BeautifulSoup
from dash import (
    dcc,
    html,
)
from flask import jsonify
from networkx.drawing.nx_agraph import graphviz_layout

from preprocessing import process_query, produce_hints

# Populate General What Ifs as a multi-select dropdown
tab_aqp_gen = html.Div(
    [
        dbc.Row(
            [
                dbc.Card(
                    [
                        html.Div("Modified Query ",
                                 style={'font-weight': 'bold'},),
                        dbc.CardBody(children="", id="general-query"),
                    ]
                )
            ]
        ),
        dbc.Row(
            [
                html.Iframe(
                    style={"width": "100%", "height": "800px"},
                    id="graph-alt-gen",
                )
            ]
        ),
    ]
)

tab_general = dcc.Dropdown(
    id="dropdown-general",
    options=[],
    multi=True,
    placeholder="Select general what-if scenarios...",
    style={"width": "100%"},
)

tab_specific_qep = dbc.Row(
    [
        dbc.ListGroup([], id="specific-whatif-list", style={"overflow": "scroll"}),
        dbc.Button(
            "Clear All",
            id="clear-interactive",
            style={"width": "100%", "margin": "0 auto"},
        ),
    ],
)

# Populate Specific What Ifs as a single-select dropdown
tab_specific = html.Div(
    [
        dcc.Dropdown(
            id="dropdown-specific",
            options=[],
            multi=False,
            placeholder="Select specific what-if scenario...",
            style={"width": "100%"},
        ),
    ]
)

tab_aqp_spec = html.Div(
    [
        dbc.Row(
            [
                dbc.Card(
                    [
                        html.Div("Modified Query "),
                        dbc.CardBody(children="", id="specific-query"),
                    ]
                ),
            ]
        ),
        dbc.Row(
            [
                html.Iframe(
                    style={"width": "100%", "height": "800px"},
                    id="graph-alt-spec",
                )
            ]
        ),
    ]
)


def create_layout():
    return html.Div(
        [
            html.Div(
                [
                    # Select Query Section
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                [
                                                    "WHAT-IF ANALYSIS OF QUERY PLANS",
                                                    dbc.Button(
                                                        "Add New Query",
                                                        id="add-query",
                                                        style={
                                                            "position": "absolute",
                                                            "right": 32,
                                                            "top": 20,
                                                        },
                                                    ),
                                                ],
                                                style={
                                                    "textAlign": "center",
                                                    "fontSize": 48,
                                                },
                                            ),
                                            html.Div(
                                                [
                                                    dcc.Dropdown(
                                                        id="schema-dropdown",
                                                        placeholder="Select a schema",
                                                        style={
                                                            "width": "50%",
                                                            "margin": "20px auto",
                                                        },
                                                    ),
                                                    dbc.Button(
                                                        "Set Database",
                                                        id="set-database-button",
                                                        color="primary",
                                                        style={
                                                            "display": "block",
                                                            "margin": "0 auto",
                                                        },
                                                    ),
                                                ]
                                            ),
                                            html.Div(
                                                id="update-message",
                                                style={
                                                    "textAlign": "center",
                                                    "marginTop": "20px",
                                                },
                                            ),
                                            dbc.CardBody(
                                                [
                                                    dbc.ListGroup(
                                                        [],
                                                        id="main-query-list",
                                                    )
                                                ],
                                                style={"overflow": "scroll"},
                                            ),
                                        ],
                                        style={"height": "800px"},
                                    )
                                ],
                                width=12,
                            )
                        ]
                    ),
                    # Query Result Section
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                ["Query Result"],
                                                class_name="border-primary fw-bold",
                                                style={"fontSize": "24px"},
                                            ),
                                            dbc.CardBody(
                                                [
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                [
                                                                    dbc.Row(
                                                                        [
                                                                            dbc.Card(
                                                                                [
                                                                                    html.Div(
                                                                                        "Original Query with Hints",
                                                                                        style={'font-weight': 'bold'}
                                                                                    ),
                                                                                    dbc.CardBody(
                                                                                        children="",
                                                                                        id="original-query",
                                                                                    ),  # placeholder children value. children should be added dynamically on aqp creation
                                                                                ],
                                                                            ),
                                                                        ],
                                                                    ),
                                                                    dbc.Row(
                                                                        [
                                                                            html.Div(
                                                                                id="query-hints",
                                                                                style={
                                                                                    "padding": "10px",
                                                                                    "marginTop": "20px",
                                                                                },
                                                                            ),
                                                                            dbc.Card(
                                                                                [
                                                                                    dbc.CardBody(
                                                                                        [
                                                                                            html.Iframe(
                                                                                                style={
                                                                                                    "width": "100%",
                                                                                                    "height": "800px",
                                                                                                    "position": "relative",
                                                                                                    "top": "65px",
                                                                                                },
                                                                                                id="graph",
                                                                                            ),
                                                                                        ]
                                                                                    ),
                                                                                ],
                                                                                style={
                                                                                    "height": "1080px"
                                                                                },
                                                                                class_name="border-primary",
                                                                            ),
                                                                        ],
                                                                    ),
                                                                ],
                                                                width=6,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Card(
                                                                        [
                                                                            dbc.CardBody(
                                                                                [
                                                                                    dbc.Row(
                                                                                        [
                                                                                            dcc.Tabs(
                                                                                                [
                                                                                                    dcc.Tab(
                                                                                                        tab_aqp_gen,
                                                                                                        value="gen-aqp-gen",
                                                                                                        label="Generate General WhatIf AQP",
                                                                                                        id="tab-aqp-gen",
                                                                                                        className="bg-primary text-white",
                                                                                                    ),
                                                                                                    dcc.Tab(
                                                                                                        tab_general,
                                                                                                        value="gen-gen",
                                                                                                        label="General What Ifs",
                                                                                                        id="tab-general",
                                                                                                    ),
                                                                                                    dcc.Tab(
                                                                                                        tab_specific,
                                                                                                        value="gen-sp",
                                                                                                        label="Specific What Ifs",
                                                                                                        id="tab-specific",
                                                                                                    ),
                                                                                                    dcc.Tab(
                                                                                                        tab_specific_qep,
                                                                                                        value="gen-qep",
                                                                                                        label="QEP",
                                                                                                        id="tab-qep",
                                                                                                    ),
                                                                                                    dcc.Tab(
                                                                                                        tab_aqp_spec,
                                                                                                        value="gen-aqp-spec",
                                                                                                        label="Generate Specific WhatIf AQP",
                                                                                                        id="tab-aqp-spec",
                                                                                                        className="bg-primary text-white",
                                                                                                    ),
                                                                                                ],
                                                                                                id="tabs",
                                                                                            ),
                                                                                            html.Div(
                                                                                                id="dropdown-placeholder",
                                                                                                style={
                                                                                                    "display": "none"
                                                                                                },
                                                                                            ),  # Hidden placeholder
                                                                                        ]
                                                                                    ),
                                                                                    dbc.Row(
                                                                                        [
                                                                                            dcc.Interval(
                                                                                                id="interval-component",
                                                                                                interval=1
                                                                                                * 1000,
                                                                                                n_intervals=0,
                                                                                            ),
                                                                                        ],
                                                                                        id="card-content",
                                                                                    ),
                                                                                ]
                                                                            ),
                                                                        ],
                                                                        style={
                                                                            "height": "1080px"
                                                                        },
                                                                        class_name="border-primary",
                                                                    ),
                                                                ]
                                                            ),
                                                        ]
                                                    ),
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                [
                                                                    dbc.Card(
                                                                        [
                                                                            dbc.CardHeader(
                                                                                [
                                                                                    "Hit Blocks"
                                                                                ],
                                                                                style={
                                                                                    "textAlign": "center"
                                                                                },
                                                                                class_name="fw-bold",
                                                                            ),
                                                                            dbc.CardBody(
                                                                                id="hit-block"
                                                                            ),
                                                                        ],
                                                                        color="info",
                                                                        style={
                                                                            "color": "white"
                                                                        },
                                                                    ),
                                                                ]
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Card(
                                                                        [
                                                                            dbc.CardHeader(
                                                                                [
                                                                                    "Read Blocks"
                                                                                ],
                                                                                style={
                                                                                    "textAlign": "center"
                                                                                },
                                                                                class_name="fw-bold",
                                                                            ),
                                                                            dbc.CardBody(
                                                                                id="read-block"
                                                                            ),
                                                                        ],
                                                                        color="info",
                                                                        style={
                                                                            "color": "white"
                                                                        },
                                                                    ),
                                                                ]
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Card(
                                                                        [
                                                                            dbc.CardHeader(
                                                                                [
                                                                                    "Buffer Size"
                                                                                ],
                                                                                style={
                                                                                    "textAlign": "center"
                                                                                },
                                                                                class_name="fw-bold",
                                                                            ),
                                                                            dbc.CardBody(
                                                                                id="buffer-size"
                                                                            ),
                                                                        ],
                                                                        color="info",
                                                                        style={
                                                                            "color": "white"
                                                                        },
                                                                    ),
                                                                ]
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Card(
                                                                        [
                                                                            dbc.CardHeader(
                                                                                [
                                                                                    "Total Cost"
                                                                                ],
                                                                                style={
                                                                                    "textAlign": "center"
                                                                                },
                                                                                class_name="fw-bold",
                                                                            ),
                                                                            dbc.CardBody(
                                                                                id="total-cost"
                                                                            ),
                                                                        ],
                                                                        color="info",
                                                                        style={
                                                                            "color": "white"
                                                                        },
                                                                    ),
                                                                ]
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Card(
                                                                        [
                                                                            dbc.CardHeader(
                                                                                [
                                                                                    "Hit Blocks"
                                                                                ],
                                                                                style={
                                                                                    "textAlign": "center"
                                                                                },
                                                                                class_name="fw-bold",
                                                                            ),
                                                                            dbc.CardBody(
                                                                                id="hit-block-alt"
                                                                            ),
                                                                        ],
                                                                        color="info",
                                                                        style={
                                                                            "color": "white"
                                                                        },
                                                                    ),
                                                                ]
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Card(
                                                                        [
                                                                            dbc.CardHeader(
                                                                                [
                                                                                    "Read Blocks"
                                                                                ],
                                                                                style={
                                                                                    "textAlign": "center"
                                                                                },
                                                                                class_name="fw-bold",
                                                                            ),
                                                                            dbc.CardBody(
                                                                                id="read-block-alt"
                                                                            ),
                                                                        ],
                                                                        color="info",
                                                                        style={
                                                                            "color": "white"
                                                                        },
                                                                    ),
                                                                ]
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Card(
                                                                        [
                                                                            dbc.CardHeader(
                                                                                [
                                                                                    "Buffer Size"
                                                                                ],
                                                                                style={
                                                                                    "textAlign": "center"
                                                                                },
                                                                                class_name="fw-bold",
                                                                            ),
                                                                            dbc.CardBody(
                                                                                id="buffer-size-alt"
                                                                            ),
                                                                        ],
                                                                        color="info",
                                                                        style={
                                                                            "color": "white"
                                                                        },
                                                                    ),
                                                                ]
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Card(
                                                                        [
                                                                            dbc.CardHeader(
                                                                                [
                                                                                    "Total Cost"
                                                                                ],
                                                                                style={
                                                                                    "textAlign": "center"
                                                                                },
                                                                                class_name="fw-bold",
                                                                            ),
                                                                            dbc.CardBody(
                                                                                id="total-cost-alt"
                                                                            ),
                                                                        ],
                                                                        color="info",
                                                                        style={
                                                                            "color": "white"
                                                                        },
                                                                    ),
                                                                ]
                                                            ),
                                                        ],
                                                        style={
                                                            "position": "relative",
                                                            "top": "40px",
                                                        },
                                                    ),
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                [
                                                                    dbc.Card(
                                                                        [
                                                                            dbc.CardHeader(
                                                                                [
                                                                                    "Natural Language"
                                                                                ],
                                                                                style={
                                                                                    "fontSize": 24,
                                                                                    "color": "white",
                                                                                },
                                                                            ),
                                                                            dbc.CardBody(
                                                                                id="natural-language",
                                                                                style={
                                                                                    "fontSize": 18,
                                                                                    "color": "white",
                                                                                },
                                                                            ),
                                                                        ],
                                                                        color="info",
                                                                    ),
                                                                ]
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Card(
                                                                        [
                                                                            dbc.CardHeader(
                                                                                [
                                                                                    "Natural Language"
                                                                                ],
                                                                                style={
                                                                                    "fontSize": 24,
                                                                                    "color": "white",
                                                                                },
                                                                            ),
                                                                            dbc.CardBody(
                                                                                id="natural-language-alt",
                                                                                style={
                                                                                    "fontSize": 18,
                                                                                    "color": "white",
                                                                                },
                                                                            ),
                                                                        ],
                                                                        color="info",
                                                                    ),
                                                                ]
                                                            ),
                                                        ],
                                                        style={
                                                            "position": "relative",
                                                            "top": "80px",
                                                        },
                                                    ),
                                                ]
                                            ),
                                        ],
                                        style={"height": "2000px", "margin": 8},
                                        class_name="border-primary",
                                    ),
                                ],
                                width=12,
                            ),
                        ]
                    ),
                ]
            ),
        ]
    )


class AlternativeQueryPlan:
    def __init__(self):
        self.selected_node = None
        self.selected_option = None


alt = AlternativeQueryPlan()


def build_graph(G, node, parent=None):
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
    changed = node.get("changed", False)

    label = f"{node_id}<br>Cost: {total_cost}<br>Buffer: {buffer}<br>Rows: {row_size}"
    G.add_node(node_id, label=label, type=node["Node Type"], data=node, changed=changed)

    if parent:
        G.add_edge(parent, node_id)

    if "Plans" in node:
        for child in node["Plans"]:
            build_graph(G, child, node_id)


def visualize_query_plan(plan):
    # Create a global alt instance
    global alt

    G = nx.DiGraph()
    build_graph(G, plan)

    pos = graphviz_layout(G, prog="dot")

    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1, color="#888"),
        hoverinfo="none",  
        mode="lines",
    )

    node_x = []
    node_y = []
    node_details = []
    node_labels = []
    node_hover_texts = []  
    node_colors = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

        details = G.nodes[node]["data"]
        buffer_sum = sum(
            details.get(key, 0)
            for key in [
                "Shared Hit Blocks",
                "Shared Read Blocks",
                "Shared Dirtied Blocks",
                "Shared Written Blocks",
            ]
        )
        node_type = details.get("Node Type", "N/A")

        # Create detailed hover text
        hover_text = (
            f"Node Type: {node_type}<br>"
            f"Node ID: {node}<br>"
            f"Total Cost: {details.get('Total Cost', 'N/A')}<br>"
            f"Buffer: {buffer_sum}<br>"
            f"Rows: {details.get('Actual Rows', 'N/A')}<br>"
        )
        node_hover_texts.append(hover_text)

        display_label = f"{node}<br>Cost: {details.get('Total Cost', 'N/A')}"
        node_labels.append(display_label)

        # Set what if options based on node type
        if node_type in ["Hash Join", "Merge Join", "Nested Loop"]:
            options = ["Hash Join", "Merge Join", "Nested Loop"]
        elif node_type in ["Seq Scan", "Index Scan", "Bitmap Heap Scan"]:
            options = ["Seq Scan", "Index Scan", "Bitmap Heap Scan"]
        else:
            options = []

        hint = produce_hints(details) if produce_hints(details) else None

        node_info = {
            "type": node_type,
            "cost": details.get("Total Cost", "N/A"),
            "rows": details.get("Actual Rows", "N/A"),
            "buffer": buffer_sum,
            "options": options,
            "changed": G.nodes[node]["changed"],
            "node_id": node,
            "hint": hint,
        }
        node_details.append(node_info)

        # Set node color based on the "changed" field
        if G.nodes[node]["changed"]:
            node_colors.append("red")
        else:
            node_colors.append("lightblue")

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        marker=dict(
            size=20,
            color=node_colors,
            line_width=2,
            symbol="circle",
        ),
        text=node_labels,
        hovertext=node_hover_texts,  # Added separate hover text
        hoverinfo="text",
        textposition="bottom center",
        customdata=node_details,
        textfont=dict(size=12),
    )

    fig = go.Figure(data=[edge_trace, node_trace])

    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )

    plot_json = fig.to_json()

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 0;
                width: 100vw;
                height: 100vh;
                overflow: hidden;
            }}
            #chart {{
                width: 100%;
                height: 100vh;
            }}
            #popup {{
                display: none;
                position: fixed;
                background: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                z-index: 1000;
                max-width: 300px;
            }}
            .option {{
                padding: 10px;
                margin: 5px 0;
                cursor: pointer;
                border-radius: 4px;
                background: #f0f0f0;
            }}
            .option:hover {{
                background: #e0e0e0;
            }}
            #details {{
                margin-bottom: 15px;
                padding: 10px;
                background: #f5f5f5;
                border-radius: 4px;
            }}
            #options-title {{
                font-weight: bold;
                margin-bottom: 10px;
            }}
            #selected-info {{
                position: fixed;
                bottom: 20px;
                left: 20px;
                background: white;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                z-index: 1000;
            }}
        </style>
    </head>
    <body>
        <div id="chart"></div>
        <div id="popup">
            <div id="details"></div>
            <div id="options-title">What if I change the operation to...</div>
            <div id="options-container"></div>
        </div>
        <div id="selected-info"></div>
        
        <script>
            var plotData = {plot_json};
            var currentNode = null;
            var selectedNode = null;
            var selectedOption = null;
            var popup = document.getElementById('popup');
            var clickListener = null;
            
            function updatePlotSize() {{
                var chart = document.getElementById('chart');
                Plotly.relayout(chart, {{
                    width: window.innerWidth,
                    height: window.innerHeight
                }});
            }}
            
            function closePopup() {{
                popup.style.display = 'none';
                if (clickListener) {{
                    document.removeEventListener('click', clickListener);
                    clickListener = null;
                }}
            }}
            
            function handleClickOutside(e) {{
                if (!popup.contains(e.target)) {{
                    closePopup();
                }}
            }}
            
            function showPopup(x, y) {{
                popup.style.display = 'block';
                
                var rect = popup.getBoundingClientRect();
                if (x + rect.width > window.innerWidth) {{
                    x = window.innerWidth - rect.width - 10;
                }}
                if (y + rect.height > window.innerHeight) {{
                    y = window.innerHeight - rect.height - 10;
                }}
                
                popup.style.left = x + 'px';
                popup.style.top = y + 'px';
                
                if (!clickListener) {{
                    clickListener = handleClickOutside;
                    setTimeout(() => {{
                        document.addEventListener('click', clickListener);
                    }}, 0);
                }}
            }}
            
            function generateOptionButtons() {{
                var optionsContainer = document.getElementById('options-container');
                optionsContainer.innerHTML = '';

                if (currentNode && currentNode.options.length > 0) {{
                    currentNode.options.forEach(option => {{
                        var optionElement = document.createElement('div');
                        optionElement.className = 'option';
                        optionElement.textContent = option;
                        optionElement.onclick = () => selectOption(option);
                        optionsContainer.appendChild(optionElement);
                    }});
                }} else {{
                    optionsContainer.innerHTML = '<div class="option">No what-if options available</div>';
                }}
            }}
            
            Plotly.newPlot('chart', plotData.data, plotData.layout).then(function() {{
                updatePlotSize();
                
                var myPlot = document.getElementById('chart');
                myPlot.on('plotly_click', function(data) {{
                    var point = data.points[0];
                    currentNode = point.customdata;
                    selectedNode = currentNode.type;
                    selectedNodeId = currentNode.node_id;
                    selectedHint = currentNode.hint;
                    
                    var details = document.getElementById('details');
                    details.innerHTML = `
                        <strong>Node Type:</strong> ${{currentNode.type}}<br>
                        <strong>Node ID:</strong> ${{currentNode.node_id}}<br>
                        <strong>Total Cost:</strong> ${{currentNode.cost}}<br>
                        <strong>Rows:</strong> ${{currentNode.rows}}<br>
                        <strong>Buffer:</strong> ${{currentNode.buffer}}
                    `;
                    
                    generateOptionButtons();
                    showPopup(data.event.pageX + 10, data.event.pageY + 10);
                    data.event.stopPropagation();
                }});
            }});
            
            window.addEventListener('resize', updatePlotSize);
            
            function selectOption(option) {{
                if (currentNode) {{
                    selectedOption = option;
                    
                    document.getElementById('selected-info').innerHTML = `
                        Last Selection:<br>
                        Node: ${{selectedNode}}<br>
                        Node ID: ${{selectedNodeId}} <br>
                        What-if: ${{selectedOption}}
                    `;
                    
                    fetch('/nodeclick', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            node_type: selectedNode,
                            node_id: selectedNodeId,
                            what_if: selectedOption,
                            hint: selectedHint
                        }})
                    }});
                    
                    closePopup();
                }}
            }}

            popup.addEventListener('click', function(e) {{
                e.stopPropagation();
            }});
        </script>
    </body>
    </html>
    """

    # Generate timestamp for filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"static/query_plan_visualization_{timestamp}.html"

    # Save the HTML content to a file with the timestamped filename
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    return filename


def convert_html_to_dash(html_input):
    def parse_html(html_text):
        soup = BeautifulSoup(html_text, "html.parser")
        components = []

        for element in soup:
            if isinstance(element, str):
                components.append(element)
            elif element.name == "b":
                components.append(html.B(element.text))
            else:
                components.append(element.text)

        return components

    if isinstance(html_input, list):
        result = []
        for html_text in html_input:
            result.extend(parse_html(html_text))
            result.append(html.Br())  # Add a line break between entries
        return result
    else:
        return parse_html(html_input)


def run_query(
    query,
):
    if query:
        query = re.sub(r"\s+", " ", query)

        result = {"query": query}

        has_error, response = process_query(query)
        if has_error:
            result["error"] = response["msg"]
        else:
            specific_what_if = response["specific_what_if"]
            general_what_if = response["general_what_if"]
            query_with_hints = response["query_with_hints"]
            json_path = response["plan_data_path"]
            with open(json_path, "r") as json_file:
                plan = json.load(json_file)
            url = visualize_query_plan(plan)  # Define this function based on your needs
            image_url = f"{url}"

            result["data"] = {
                "imageUrl": image_url,
                "hints": response["hints"],
                "modifiedQuery": response["query_with_hints"],
                "generalWhatif": response["general_what_if"],
                "specificWhatif": response["specific_what_if"],
                "additionalDetails": {
                    "naturalExplanation": response["natural_explain"],
                    "totalCost": response["summary_data"]["total_cost"],
                    "totalBlocks": response["summary_data"]["total_blocks"],
                    "totalNodes": response["summary_data"]["nodes_count"],
                },
            }

        return query_with_hints, specific_what_if, general_what_if, jsonify(result)
    return jsonify({"error": "No query provided"})


def read_graph(target):
    with open(target, "r") as file:
        custom_html = file.read()
    return custom_html


def update_costs(data):
    hit = data["additionalDetails"]["totalBlocks"]["hit_blocks"]
    read = data["additionalDetails"]["totalBlocks"]["read_blocks"]
    size = hit + read
    total = data["additionalDetails"]["totalCost"]

    return hit, read, total, size
