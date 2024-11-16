import networkx as nx
import plotly.graph_objects as go
from networkx.drawing.nx_agraph import graphviz_layout
import datetime
from preprocessing import produce_hints


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

    label = f"{node['Node Type']}<br>Node ID: {node_id}<br>Cost: {total_cost}<br>Buffer: {buffer}<br>Rows: {row_size}"
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

        # Set what if options based on node type
        if node_type in ["Hash Join", "Merge Join", "Nested Loop"]:
            options = ["Hash Join", "Merge Join", "Nested Loop"]
        elif node_type in ["Seq Scan", "Index Scan", "Bitmap Heap Scan"]:
            options = ["Seq Scan", "Index Scan", "Bitmap Heap Scan"]
        else:
            options = []

        hint = produce_hints(details) if produce_hints(details) else None

        node_info = {
            "type": details.get("Node Type", "N/A"),
            "cost": details.get("Total Cost", "N/A"),
            "rows": details.get("Actual Rows", "N/A"),
            "buffer": buffer_sum,
            "options": options,
            "changed": G.nodes[node]["changed"],
            "node_id": node,
            "hint": hint,
        }
        node_details.append(node_info)
        node_labels.append(G.nodes[node]["label"])

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
        hoverinfo="text",
        textposition="bottom center",
        customdata=node_details,
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
                // Remove the click listener when popup is closed
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
                
                // Position the popup
                var rect = popup.getBoundingClientRect();
                if (x + rect.width > window.innerWidth) {{
                    x = window.innerWidth - rect.width - 10;
                }}
                if (y + rect.height > window.innerHeight) {{
                    y = window.innerHeight - rect.height - 10;
                }}
                
                popup.style.left = x + 'px';
                popup.style.top = y + 'px';
                
                // Add click listener only when popup is shown
                if (!clickListener) {{
                    clickListener = handleClickOutside;
                    // Use setTimeout to avoid immediate closure
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
                    
                    console.log('Node clicked:', selectedNodeId);
                    
                    var details = document.getElementById('details');
                    details.innerHTML = `
                        <strong>Node Type:</strong> ${{currentNode.type}}<br>
                        <strong>Total Cost:</strong> ${{currentNode.cost}}<br>
                        <strong>Rows:</strong> ${{currentNode.rows}}<br>
                        <strong>Buffer:</strong> ${{currentNode.buffer}}
                    `;
                    
                    generateOptionButtons();
                    showPopup(data.event.pageX + 10, data.event.pageY + 10);
                    // Stop propagation to prevent immediate popup closure
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
                    
                    console.log('Selected:', {{
                        node_type: selectedNode,
                        node_id: selectedNodeId,
                        what_if: selectedOption
                    }});
                    
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

            // Prevent popup closure when clicking inside it
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

    print(f"HTML file saved as {filename}")
    # fig.show()
    # return alt
    return filename
    # return fig
