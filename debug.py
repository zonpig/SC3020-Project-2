from dash import (
    Dash,
    dcc,
    html,
    Input,
    Output,
    State,
    ALL,
    ctx,
)
import dash_bootstrap_components as dbc
import re

from helper import (
    extract_tables_from_query,
    run_query,
    read_graph,
    update_costs,
    convert_html_to_dash,
)
from whatif3 import what_if

from flask import Flask, request, jsonify
import datetime

server = Flask(__name__)
app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.LUX])

# Global variables
queryid = None  # Placeholder logic. queryid can be local variable if modified query is known before execution
query_with_hints_global = None  # Global variable to store query_with_hints


# Pre populating input queries
eg1 = "SELECT customer.c_name, nation.n_name FROM customer, nation WHERE customer.c_nationkey = nation.n_nationkey and customer.c_acctbal <= 5 and nation.n_nationkey <= 5"
eg2 = "select sum(l_extendedprice * l_discount) as revenue from lineitem where l_shipdate >= date '1995-01-01' and l_shipdate < date '1995-01-01' + interval '1' year and l_discount between 0.09 - 0.01 and 0.09 + 0.01 and l_quantity < 24;"

# Populate General What Ifs as a multi-select dropdown
tab_aqp_gen = html.Div(
    [
        dbc.Row(
            [
                dbc.Card(
                    [
                        dbc.CardBody(
                            children="whats up gang", id="general-query"
                        )  # placeholder children value. children should be added dynamically on aqp creation
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
        dbc.ListGroup([], id="specific-whatif-list"),
    ]
)


tab_aqp_spec = html.Div(
    [
        dbc.Row(
            [
                dbc.Card(
                    [
                        dbc.CardBody(
                            children="whats up gang", id="specific-query"
                        )  # placeholder children value. children should be added dynamically on aqp creation
                    ]
                )
            ]
        ),
        dbc.Row(
            [
                html.Iframe(
                    style={"width": "100%", "height": "800px"},
                    id="graph-alt",
                )
            ]
        ),
    ]
)

app.layout = html.Div(
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
                                                "SQL Queries",
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
                                        dbc.CardBody(
                                            [
                                                dbc.ListGroup(
                                                    [
                                                        dbc.ListGroupItem(
                                                            [
                                                                dbc.Input(
                                                                    type="text",
                                                                    value=eg1,
                                                                    id={
                                                                        "type": "query-text",
                                                                        "index": 0,
                                                                    },
                                                                ),
                                                                dbc.Button(
                                                                    "Run Query",
                                                                    id={
                                                                        "type": "run-query",
                                                                        "index": 0,
                                                                    },
                                                                    style={
                                                                        "margin": 8,
                                                                        "height": "50px",
                                                                    },
                                                                ),
                                                                dbc.Button(
                                                                    "Delete Query",
                                                                    id={
                                                                        "type": "delete-query",
                                                                        "index": 0,
                                                                    },
                                                                    style={
                                                                        "margin": 8,
                                                                        "height": "50px",
                                                                    },
                                                                ),
                                                            ],
                                                            color="primary",
                                                            style={"margin": 2},
                                                            id={
                                                                "type": "query",
                                                                "index": 0,
                                                            },
                                                        ),
                                                        dbc.ListGroupItem(
                                                            [
                                                                dbc.Input(
                                                                    type="text",
                                                                    value=eg2,
                                                                    id={
                                                                        "type": "query-text",
                                                                        "index": 1,
                                                                    },
                                                                ),
                                                                dbc.Button(
                                                                    "Run Query",
                                                                    id={
                                                                        "type": "run-query",
                                                                        "index": 1,
                                                                    },
                                                                    style={
                                                                        "margin": 8,
                                                                        "height": "50px",
                                                                    },
                                                                ),
                                                                dbc.Button(
                                                                    "Delete Query",
                                                                    id={
                                                                        "type": "delete-query",
                                                                        "index": 1,
                                                                    },
                                                                    style={
                                                                        "margin": 8,
                                                                        "height": "50px",
                                                                    },
                                                                ),
                                                            ],
                                                            color="primary",
                                                            style={"margin": 2},
                                                            id={
                                                                "type": "query",
                                                                "index": 1,
                                                            },
                                                        ),
                                                    ],
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
                                                                                dbc.CardBody(
                                                                                    children="IMPRESSING THE BRUZZ",
                                                                                    id="original-query",
                                                                                )  # placeholder children value. children should be added dynamically on aqp creation
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
                                                                                "height": "900px"
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
                                                                        "height": "960px"
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


# Callback to add or delete query list
@app.callback(
    Output("main-query-list", "children"),
    [
        Input("add-query", "n_clicks"),
        Input({"type": "delete-query", "index": ALL}, "n_clicks"),
    ],
    [State("main-query-list", "children")],
)
def update_query_list(n1, n2, children):
    children = children or []  # Ensure children is a list
    if (
        n2
        and isinstance(ctx.triggered_id, dict)
        and ctx.triggered_id["type"] == "delete-query"
    ):
        index_to_delete = ctx.triggered_id["index"]
        children = [
            child
            for child in children
            if child["props"]["id"]["index"] != index_to_delete
        ]
    elif n1 and ctx.triggered_id == "add-query":
        new_index = len(children)
        new_item = dbc.ListGroupItem(
            [
                dbc.Input(type="text", id={"type": "query-text", "index": new_index}),
                dbc.Button("Run Query", id={"type": "run-query", "index": new_index}),
                dbc.Button(
                    "Delete Query", id={"type": "delete-query", "index": new_index}
                ),
            ],
            color="primary",
            style={"margin": 2},
            id={"type": "query", "index": new_index},
        )
        children.append(new_item)
    return children


@app.callback(
    [
        Output("graph", "srcDoc"),
        Output("natural-language", "children"),
        Output("hit-block", "children"),
        Output("read-block", "children"),
        Output("total-cost", "children"),
        Output("buffer-size", "children"),
        Output("tab-general", "children"),
        Output("tab-specific", "children"),
        Output("query-hints", "children"),  # New output for query_with_hints
    ],
    [Input({"type": "run-query", "index": ALL}, "n_clicks")],
    [State("main-query-list", "children")],
)
def draw_graph(n1, children):
    global query_with_hints_global  # Declare the global variable
    if not any(n1 or []):
        return "", "", "", "", "", "", [], [], ""
    if n1:
        if (
            isinstance(ctx.triggered_id, dict)
            and ctx.triggered_id["type"] == "run-query"
        ):
            print(f"\nrun id is : {ctx.triggered_id}")
            global queryid
            queryid = ctx.triggered_id["index"]
            for i, child in enumerate(children):
                if child["props"]["id"]["index"] == queryid:
                    query = child["props"]["children"][0]["props"]["value"]
                    n_query = re.sub(r"\n|\t", " ", query).strip()
                    print(f"the query is : {n_query.upper()}")
                    tables_extracted = extract_tables_from_query(n_query.upper())
                    query_with_hints, specific_what_if, general_what_if, response = (
                        run_query(n_query, tables_extracted)
                    )
                    query_with_hints_global = query_with_hints
                    print(query_with_hints_global)
                    results = response.get_json()  # Extract JSON data from the response
                    if "error" in results:
                        print(f"Error: {results['error']}")
                    else:
                        print(f'Image URL: {results["data"]["imageUrl"]}')
                        data = results["data"]
                        natural_explanation = data["additionalDetails"][
                            "naturalExplanation"
                        ]
                        natural = natural_explanation
                        natural = convert_html_to_dash(natural)
                        imageurl = data["imageUrl"]
                        custom_html = read_graph(imageurl)
                        hit, read, total, size = update_costs(data)
                        # Populate General What Ifs as a multi-select dropdown
                        general_dropdown = dcc.Dropdown(
                            id="dropdown-general",
                            options=[
                                {"label": option, "value": option}
                                for option in general_what_if
                            ],
                            multi=True,
                            placeholder="Select general what-if scenarios...",
                            style={"width": "100%"},
                        )

                        # Populate Specific What Ifs as a single-select dropdown
                        specific_dropdown = dcc.Dropdown(
                            id="dropdown-specific",
                            options=[
                                {"label": option, "value": option}
                                for option in specific_what_if
                            ],
                            multi=False,
                            placeholder="Select specific what-if scenario...",
                            style={"width": "100%"},
                        )

                        # Wrap query_with_hints in a Div
                        query_hints_div = html.Div(
                            f"Query with Hints: {query_with_hints}",
                            style={"fontSize": "16px", "color": "blue"},
                        )

                        return (
                            custom_html,
                            natural,
                            hit,
                            read,
                            total,
                            size,
                            general_dropdown,
                            specific_dropdown,
                            query_hints_div,
                        )
    return "", "", "", "", "", "", "", "", ""


@app.callback(
    Output("specific-whatif-list", "children"),
    [
        Input("interval-component", "n_intervals"),
        Input({"type": "run-query", "index": ALL}, "n_clicks"),
    ],
    State("specific-whatif-list", "children"),
)
def update_card(n_intervals, n1, children):
    # Reset specific what if when new query is ran
    if n1:
        # Check that trigger is run query
        if (
            isinstance(ctx.triggered_id, dict)
            and ctx.triggered_id["type"] == "run-query"
        ):
            children = []
            return children

    if children is None:
        children = []
    if selections:
        for select in selections:
            nodeid = select["node_id"]
            whatif = select["what_if"]
            if nodeid:
                text = f"Node id = {nodeid} | What if = {whatif}"
                updated = False
                for i, child in enumerate(children):
                    if child["props"]["id"] == str(nodeid):
                        child["props"]["children"] = text
                        updated = True
                        break
                if not updated:
                    new_item = dbc.ListGroupItem([text], id=str(nodeid))
                    children.append(new_item)
    return children


# Logic for dropdowns
selected_options = []  # This will store the current dropdown selections


@app.callback(
    Output("dropdown-placeholder", "children"),  # Single shared output
    [
        Input("dropdown-general", "value"),
        Input("dropdown-specific", "value"),
        Input("tabs", "value"),
    ],
)
def handle_tab_and_dropdown_changes(general_value, specific_value, active_tab):
    global selected_options

    if not ctx.triggered:
        return ""

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "tabs":
        print(f"Active tab: {active_tab}")
        # Reset the selected options when the tab changes
        if active_tab != "gen-aqp-spec" and active_tab != "gen-aqp-gen":
            selected_options = []
            print(f"Reset selected options due to tab change: {selected_options}")
    elif trigger_id == "dropdown-general" and active_tab == "gen-gen":
        # Update for General What Ifs
        if general_value:
            selected_options = general_value  # Multi-select values
            print(f"Updated selected options (general): {selected_options}")
    elif trigger_id == "dropdown-specific" and active_tab == "gen-sp":
        # Update for Specific What Ifs
        if specific_value:
            selected_options = [specific_value]  # Single-select value as a list
            print(f"Updated selected options (specific): {selected_options}")

    return ""  # Placeholder output to satisfy Dash requirements


# AQP generation callback
@app.callback(
    [
        Output("graph-alt", "srcDoc"),
        Output("natural-language-alt", "children", allow_duplicate=True),
        Output("hit-block-alt", "children", allow_duplicate=True),
        Output("read-block-alt", "children", allow_duplicate=True),
        Output("total-cost-alt", "children", allow_duplicate=True),
        Output("buffer-size-alt", "children", allow_duplicate=True),
    ],
    [Input("tabs", "value")],
    [State("main-query-list", "children")],
    prevent_initial_call=True,
)
def generate_aqp_specific(tab, children):
    global selected_options
    global query_with_hints_global  # Use the global variable
    print(f"Current tab: {tab}")
    if tab == "gen-aqp-spec":
        print(f"Starting AQP generation with options: {selected_options}")
        global queryid
        print(f"STARTING ALTERNATE RUN {queryid}")
        for i, child in enumerate(children):
            if child["props"]["id"]["index"] == queryid:
                query = child["props"]["children"][0]["props"]["value"]
                n_query = re.sub(r"\n|\t", " ", query).strip()
                print(f"The query is: {n_query.upper()}")
                tables_extracted = extract_tables_from_query(n_query.upper())
                response = what_if(
                    query_with_hints_global, tables_extracted, selected_options
                )
                results = response.get_json()  # Extract JSON data from the response
                if "error" in results:
                    print(f"Error: {results['error']}")
                else:
                    print(f'Image URL: {results["data"]["imageUrl"]}')
                    data = results["data"]
                    natural_explanation = data["additionalDetails"][
                        "naturalExplanation"
                    ]
                    natural = convert_html_to_dash(natural_explanation)
                    imageurl = data["imageUrl"]
                    custom_html = read_graph(imageurl)
                    hit, read, total, size = update_costs(data)
                    return custom_html, natural, hit, read, total, size

    # # Generating AQP for general
    # elif tab == "gen-aqp-gen":
    #     print(f"\nSTARTING ALTERNATE RUN {queryid}")
    #     for i, child in enumerate(children):
    #         if child["props"]["id"]["index"] == queryid:
    #             query = child["props"]["children"][0]["props"]["value"]
    #             n_query = re.sub(r"\n|\t", " ", query).strip()
    #             print(f"the query is : {n_query.upper()}")
    #             tables_extracted = extract_tables_from_query(n_query.upper())
    #             response = run_query(n_query, tables_extracted)
    #             results = response.get_json()  # Extract JSON data from the response
    #             if "error" in results:
    #                 print(f"Error: {results["error"]}")
    #             else:
    #                 print(f"Image URL: {results["data"]["imageUrl"]}")
    #                 data = results["data"]
    #                 natural_explanation = data["additionalDetails"][
    #                     "naturalExplanation"
    #                 ]
    #                 natural = natural_explanation
    #                 natural = convert_html_to_dash(natural)
    #                 imageurl = data["imageUrl"]
    #                 custom_html = read_graph(imageurl)
    #                 hit, read, total, size = update_costs(data)
    #                 return custom_html, natural, hit, read, total, size

    return "", "", "", "", "", ""


"""
def generate_aqp_specific(n1, n2, query_list):
    if not (n1 and n2):
        return "", "", "", "", "", ""
        
    try:
        current_query = next((child["props"]["children"][0]["props"]["value"] 
                            for child in query_list 
                            if child["props"]["children"][0]["props"].get("value")), None)
        
        if not current_query:
            raise ValueError("No query found")
        
        print(f"\nFUCK ME WHAT IS MY CURRENT QUERY : {current_query}")
        n_query = re.sub(r"\n|\t", " ", current_query).strip()
        tables_extracted = extract_tables_from_query(n_query.upper())
            
        selections_response = requests.get("http://localhost:8050/get-selections")
        selections_data = selections_response.json()
        print(selections_data)
        response = run_query(current_query, tables_extracted)
        
        results = response.get_json()
        if "error" in results:
            raise ValueError(results["error"])
        
        data = results["data"]
        natural = convert_html_to_dash(data["additionalDetails"]["naturalExplanation"])
        custom_html = read_graph(data["imageUrl"])
        hit, read, total, size = update_costs(data)
        
        return custom_html, natural, hit, read, total, size
            
    except Exception as e:
        print(f"Error generating AQP: {str(e)}")
        return dash.no_update
"""
# SERVER CALLS
selections = []


@server.route("/nodeclick", methods=["POST"])
def receive_nodeclick():
    data = request.get_json()
    current_selection = {
        "timestamp": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
        "node_type": data.get("type"),
        "node_id": data.get("node_id"),
        "what_if": data.get("what_if"),
    }

    # Update or append selection
    node_index = next(
        (
            i
            for i, s in enumerate(selections)
            if s["node_id"] == current_selection["node_id"]
        ),
        -1,
    )

    if node_index >= 0:
        selections[node_index] = current_selection
    else:
        selections.append(current_selection)

    print(selections)
    return jsonify({"status": "success"})


@server.route("/get-selections", methods=["GET"])
def get_selections():
    global selections
    response = jsonify(selections)
    selections = []
    return response


if __name__ == "__main__":
    app.run_server(debug=True)