import datetime
import re

import dash_bootstrap_components as dbc
from dash import (
    ALL,
    Dash,
    Input,
    Output,
    State,
    ctx,
    dcc,
)
from dash.exceptions import PreventUpdate
from flask import Flask, jsonify, request

from interface import (
    convert_html_to_dash,
    create_layout,
    read_graph,
    run_query,
    update_costs,
)
from preprocessing import Database, get_postgres_schemas
from whatif import what_if

server = Flask(__name__)
app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.LUX])

# Global variables
queryid = None
query_with_hints_global = None  # Store query_with_hints
selected_options = []  # Store the current dropdown selections
selections = []  # Stores the current node click selections

# Pre populating input queries
example_queries = [
    "SELECT customer.c_name, nation.n_name FROM customer, nation WHERE customer.c_nationkey = nation.n_nationkey and customer.c_acctbal >= 5 and nation.n_nationkey >= 5",
    "select c.c_name, n.n_name, sum(l.l_extendedprice * (1 - l.l_discount)) as total_revenue from customer c join orders o on c.c_custkey = o.o_custkey join lineitem l on o.o_orderkey = l.l_orderkey join nation n on c.c_nationkey = n.n_nationkey where o.o_orderdate >= date '1993-01-01' and o.o_orderdate < date '1993-01-01' + interval '7' day and l.l_discount < 0.01 group by c.c_name, n.n_name order by total_revenue desc;",
    "select ps_partkey, sum(ps_supplycost * ps_availqty) as value from partsupp, supplier, nation where ps_suppkey = s_suppkey and s_nationkey = n_nationkey and n_name = 'SAUDI ARABIA' group by ps_partkey having sum(ps_supplycost * ps_availqty) > (select sum(ps_supplycost * ps_availqty) * 0.0001000000 from partsupp, supplier, nation where ps_suppkey = s_suppkey and s_nationkey = n_nationkey and n_name = 'SAUDI ARABIA') order by value desc limit 1;",
]

app.layout = create_layout()


# Reset global variables on app restart
@server.before_request
def reset_globals():
    server.before_request_funcs[None].remove(reset_globals)

    global selected_options, selections, queryid, query_with_hints_global
    selected_options, selections, queryid, query_with_hints_global = [], [], None, None


# Callback to populate the dropdown
@app.callback(
    [
        Output("schema-dropdown", "options"),
        Output("schema-dropdown", "value"),
        Output("main-query-list", "children"),
    ],
    Input("schema-dropdown", "id"),
)
def load_schemas_and_queries(_):
    global example_queries
    try:
        schemas = get_postgres_schemas()  # Fetch schemas dynamically
        options = [{"label": schema, "value": schema} for schema in schemas]

        # Default schema selection
        default_value = "TPC-H" if "TPC-H" in schemas else None

        # Populate queries if schema is TPC-H
        queries_list = []
        if default_value == "TPC-H":
            for idx, query in enumerate(example_queries):
                queries_list.append(
                    dbc.ListGroupItem(
                        [
                            dbc.Input(
                                type="text",
                                value=query,
                                id={"type": "query-text", "index": idx},
                            ),
                            dbc.Button(
                                "Run Query",
                                id={"type": "run-query", "index": idx},
                                style={"margin": 8, "height": "50px"},
                            ),
                            dbc.Button(
                                "Delete Query",
                                id={"type": "delete-query", "index": idx},
                                style={"margin": 8, "height": "50px"},
                            ),
                        ],
                        color="primary",
                        style={"margin": 2},
                        id={"type": "query", "index": idx},
                    )
                )

        return options, default_value, queries_list
    except Exception as e:
        print(f"Error fetching schemas or queries: {e}")
        return [], None, []


# Callback to set the database
@app.callback(
    Output("update-message", "children"),
    Output("main-query-list", "children", allow_duplicate=True),
    Input("set-database-button", "n_clicks"),
    State("schema-dropdown", "value"),
    prevent_initial_call=True,
)
def set_database(n_clicks, selected_schema):
    if n_clicks is None:
        raise PreventUpdate
    if not selected_schema:
        return "Please select a schema before setting the database."
    try:
        if selected_schema:
            # Update the database in the Database class
            Database.set_database(selected_schema)
            queries_list = []
            if selected_schema == "TPC-H":
                for idx, query in enumerate(example_queries):
                    queries_list.append(
                        dbc.ListGroupItem(
                            [
                                dbc.Input(
                                    type="text",
                                    value=query,
                                    id={"type": "query-text", "index": idx},
                                ),
                                dbc.Button(
                                    "Run Query",
                                    id={"type": "run-query", "index": idx},
                                    style={"margin": 8, "height": "50px"},
                                ),
                                dbc.Button(
                                    "Delete Query",
                                    id={"type": "delete-query", "index": idx},
                                    style={"margin": 8, "height": "50px"},
                                ),
                            ],
                            color="primary",
                            style={"margin": 2},
                            id={"type": "query", "index": idx},
                        )
                    )
            return f"Database updated to {selected_schema} successfully.", queries_list

        else:
            return "error", "Failed to update database.", []
    except Exception as e:
        print(f"Error setting database: {e}")
        return "An error occurred while setting the database."


# Callback to add or delete query list
@app.callback(
    Output("main-query-list", "children", allow_duplicate=True),
    [
        Input("add-query", "n_clicks"),
        Input({"type": "delete-query", "index": ALL}, "n_clicks"),
    ],
    State("main-query-list", "children"),
    prevent_initial_call=True,
)
def update_query_list(n1, n2, children):
    # Ensure children is a list
    children = children or []

    # Deletion logic
    if n2:
        for i, delete_click in enumerate(n2):
            if delete_click:  # Check which button was clicked
                index_to_delete = ctx.triggered_id["index"]
                # Remove the query with the matching index
                children = [
                    child
                    for child in children
                    if child["props"]["id"]["index"] != index_to_delete
                ]
                return children

    # Addition logic
    if n1 and ctx.triggered_id == "add-query":
        new_index = len(children)  # Use current length of children for new index
        new_item = dbc.ListGroupItem(
            [
                dbc.Input(
                    type="text",
                    id={"type": "query-text", "index": new_index},
                    value="",  # Provide an empty query for the new input
                ),
                dbc.Button(
                    "Run Query",
                    id={"type": "run-query", "index": new_index},
                    style={"margin": 8, "height": "50px"},
                ),
                dbc.Button(
                    "Delete Query",
                    id={"type": "delete-query", "index": new_index},
                    style={"margin": 8, "height": "50px"},
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
        Output("original-query", "children"),
        Output("graph-alt-spec", "srcDoc", allow_duplicate=True),
        Output("graph-alt-gen", "srcDoc", allow_duplicate=True),
        Output("specific-query", "children", allow_duplicate=True),
        Output("general-query", "children", allow_duplicate=True),
        Output("natural-language-alt", "children", allow_duplicate=True),
        Output("hit-block-alt", "children", allow_duplicate=True),
        Output("read-block-alt", "children", allow_duplicate=True),
        Output("total-cost-alt", "children", allow_duplicate=True),
        Output("buffer-size-alt", "children", allow_duplicate=True),
    ],
    [Input({"type": "run-query", "index": ALL}, "n_clicks")],
    [State("main-query-list", "children")],
    prevent_initial_call=True,
)
def draw_graph(n1, children):
    global query_with_hints_global
    if not any(n1 or []):
        return "", "", "", "", "", "", [], [], "", "", "", "", "", "", "", "", "", ""
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
                    query_with_hints, specific_what_if, general_what_if, response = (
                        run_query(n_query)
                    )
                    query_with_hints_global = query_with_hints
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

                        return (
                            custom_html,
                            natural,
                            hit,
                            read,
                            total,
                            size,
                            general_dropdown,
                            specific_dropdown,
                            query_with_hints,
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                        )
    return "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""


@app.callback(
    Output("specific-whatif-list", "children"),
    [
        Input("interval-component", "n_intervals"),
        Input({"type": "run-query", "index": ALL}, "n_clicks"),
        Input("clear-interactive", "n_clicks"),
    ],
    State("specific-whatif-list", "children"),
)
def update_card(n_intervals, n1, n2, children):
    global selections
    # Reset interactive what if when new query is ran
    if n1:
        # Check that trigger is run query
        if (
            isinstance(ctx.triggered_id, dict)
            and ctx.triggered_id["type"] == "run-query"
        ):
            selections = []
            children = []
            return children

    if n2:
        if ctx.triggered_id == "clear-interactive":
            children = []
            selections = []
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


@app.callback(
    [
        Output("dropdown-general", "value"),
        Output("dropdown-specific", "value"),
    ],
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
        if active_tab == "gen-qep":
            # Clears all tabs when switched to interactive
            general_value = []
            specific_value = []
            selected_options = []
    # Clears specific tab
    elif trigger_id == "dropdown-general" and active_tab == "gen-gen":
        specific_value = []
        # Update for General What Ifs
        selected_options = general_value  # Multi-select values
        print(f"Updated selected options (general): {selected_options}")
    # Clears general tab
    elif trigger_id == "dropdown-specific" and active_tab == "gen-sp":
        general_value = []
        # Update for Specific What Ifs
        selected_options = [specific_value]  # Single-select value as a list
        print(f"Updated selected options (specific): {selected_options}")

    return general_value, specific_value


# AQP generation callback
@app.callback(
    [
        Output("graph-alt-spec", "srcDoc"),
        Output(
            "natural-language-alt",
            "children",
        ),
        Output(
            "hit-block-alt",
            "children",
        ),
        Output(
            "read-block-alt",
            "children",
        ),
        Output(
            "total-cost-alt",
            "children",
        ),
        Output(
            "buffer-size-alt",
            "children",
        ),
        Output("specific-query", "children"),
    ],
    [Input("tabs", "value")],
    [State("main-query-list", "children")],
    prevent_initial_call=True,
)
def generate_aqp_specific(tab, children):
    global selected_options
    global query_with_hints_global  # Use the global variable
    global selections
    global queryid

    if tab == "gen-aqp-spec":
        print(f"Current tab: {tab}")
        if selected_options:
            print(f"Starting AQP generation with options: {selected_options}")
            print(f"STARTING ALTERNATE RUN {queryid}")
            for child in children:
                if child["props"]["id"]["index"] == queryid:
                    response = what_if(query_with_hints_global, selected_options)
                    results = response.get_json()  # Extract JSON data from the response
        elif selections:
            print(f"Starting AQP generation with options: {selections}")
            print(f"STARTING ALTERNATE RUN {queryid}")
            for child in children:
                if child["props"]["id"]["index"] == queryid:
                    response = what_if(query_with_hints_global, selections)
                    results = response.get_json()  # Extract JSON data from the response
        if "error" in results:
            print(f"Error: {results['error']}")
        else:
            print(f'Image URL: {results["data"]["imageUrl"]}')
            data = results["data"]
            natural_explanation = data["additionalDetails"]["naturalExplanation"]
            natural = convert_html_to_dash(natural_explanation)
            imageurl = data["imageUrl"]
            custom_html = read_graph(imageurl)
            hit, read, total, size = update_costs(data)
            updated_query_text = results["query"]
            return custom_html, natural, hit, read, total, size, updated_query_text
    return "", "", "", "", "", "", ""


@app.callback(
    [
        Output("graph-alt-gen", "srcDoc"),
        Output("natural-language-alt", "children", allow_duplicate=True),
        Output("hit-block-alt", "children", allow_duplicate=True),
        Output("read-block-alt", "children", allow_duplicate=True),
        Output("total-cost-alt", "children", allow_duplicate=True),
        Output("buffer-size-alt", "children", allow_duplicate=True),
        Output("general-query", "children"),
    ],
    [
        Input("tabs", "value"),
    ],
    [State("main-query-list", "children")],
    prevent_initial_call=True,
)
def generate_aqp_general(tab, children):
    global selected_options
    global query_with_hints_global  # Use the global variable
    if tab == "gen-aqp-gen":
        print(f"Current tab: {tab}")
        print(f"Starting AQP generation with options: {selected_options}")
        global queryid
        print(f"STARTING ALTERNATE RUN {queryid}")
        for i, child in enumerate(children):
            if child["props"]["id"]["index"] == queryid:
                response = what_if(query_with_hints_global, selected_options)
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
                    updated_query_text = results["query"]
                    return (
                        custom_html,
                        natural,
                        hit,
                        read,
                        total,
                        size,
                        updated_query_text,
                    )
    return "", "", "", "", "", "", ""


# SERVER CALLS
@server.route("/nodeclick", methods=["POST"])
def receive_nodeclick():
    data = request.get_json()
    current_selection = {
        "timestamp": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
        "node_type": data.get("type"),
        "node_id": data.get("node_id"),
        "what_if": data.get("what_if"),
        "hint": data.get("hint"),
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

    return jsonify({"status": "success"})


@server.route("/get-selections", methods=["GET"])
def get_selections():
    global selections
    response = jsonify(selections)
    selections = []
    return response


if __name__ == "__main__":
    app.run_server(debug=True)
