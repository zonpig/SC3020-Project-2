from dash import Dash, dcc, html, Input, Output, State, MATCH, ALL, ctx, callback_context
import dash
import dash_bootstrap_components as dbc
import plotly.express as px
import re

import requests
from helper import *

from flask import Flask, request, jsonify
import datetime

server = Flask(__name__)
app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.LUX])

logs = []
eg1 = 'SELECT customer.c_name, nation.n_name FROM customer, nation WHERE customer.c_nationkey = nation.n_nationkey and customer.c_acctbal <= 5 and nation.n_nationkey <= 5'
eg2 = "select sum(l_extendedprice * l_discount) as revenue from lineitem where l_shipdate >= date '1995-01-01' and l_shipdate < date '1995-01-01' + interval '1' year and l_discount between 0.09 - 0.01 and 0.09 + 0.01 and l_quantity < 24;"

app.layout = html.Div([
    html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        'SQL Queries',
                        dbc.Button('Add New Query', id='add-query', style={'position': 'absolute', 'right': 32, 'top': 20}),
                    ],
                    style={'text-align': 'center', 'font-size': 48}),
                    dbc.CardBody([
                        dbc.ListGroup([
                            dbc.ListGroupItem(
                                [
                                    dbc.Input(type='text', value=eg1, id={'type': 'query-text', 'index': 0}),
                                    dbc.Button('Run Query', id={'type': 'run-query', 'index': 0}, style={'margin': 8, 'height': '50px'}),
                                    dbc.Button('Delete Query', id={'type': 'delete-query', 'index': 0}, style={'margin': 8, 'height': '50px'})
                                ],
                                color='primary', style={'margin': 2}, id={'type': 'query', 'index': 0}
                            ),
                            dbc.ListGroupItem(
                                [
                                    dbc.Input(type='text', value=eg2, id={'type': 'query-text', 'index': 1}),
                                    dbc.Button('Run Query', id={'type': 'run-query', 'index': 1}, style={'margin': 8, 'height': '50px'}),
                                    dbc.Button('Delete Query', id={'type': 'delete-query', 'index': 1}, style={'margin': 8, 'height': '50px'})
                                ],
                                color='primary', style={'margin': 2}, id={'type': 'query', 'index': 1}
                            )
                        ], id='main-query-list')
                    ]),
                ], style={'height': '800px'})
            ], width=12)
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(['Query Result'], class_name='border-primary fw-bold', style={'font-size': '24px'}),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Iframe(
                                    style={'width': '100%', 'height': '800px'},
                                    id='graph',
                                ),
                            ],width=6),
                            dbc.Col([
                                dbc.Card([
                                    dbc.Button('Generate AQP (Callback)', id='generate-aqp-callback', style={'text-align': 'center'}),
                                    dbc.CardHeader(['Generate AQP'], class_name='border-primary fw-bold', style={'font-size': '18px', 'text-align': 'center'}),
                                    dbc.CardBody([
                                        dbc.Row([
                                            dbc.Tabs([
                                                dbc.Tab(label='General What Ifs', tab_id='tab-general'),
                                                dbc.Tab(label='Specific What Ifs', tab_id='tab-specific'),
                                                dbc.Tab(label='Back', tab_id='tab-original'),
                                            ], id='tabs', active_tab='tab-original'),
                                        ]),
                                        dbc.Row([], id='card-content')
                                    ]),
                                ], style={'height': '800px'}, class_name='border-primary'),
                            ])
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader(['Hit Blocks'], style={'text-align': 'center'}, class_name='fw-bold'),
                                    dbc.CardBody(id='hit-block'),
                                ], color='info', style={'color': 'white'}),
                            ]),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader(['Read Blocks'], style={'text-align': 'center'}, class_name='fw-bold'),
                                    dbc.CardBody(id='read-block'),
                                ], color='info', style={'color': 'white'}),
                            ]),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader(['Buffer Size'], style={'text-align': 'center'}, class_name='fw-bold'),
                                    dbc.CardBody(id='buffer-size'),
                                ], color='info', style={'color': 'white'}),
                            ]),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader(['Total Cost'], style={'text-align': 'center'}, class_name='fw-bold'),
                                    dbc.CardBody(id='total-cost'),
                                ], color='info', style={'color': 'white'}),
                            ]),
                        ], style={'width': '50%'}),
                        dbc.Row([
                            dbc.Card([
                                dbc.CardHeader(['Natural Language'], style={'font-size': 24, 'color': 'white'}),
                                dbc.CardBody(id='natural-language', style={'font-size': 18, 'color': 'white'}),
                            ], color='info'),
                        ], style={'margin': 12}),
                    ]),
                ], style={'height': '1200px', 'margin': 8}, class_name='border-primary'),
            ], width=12),
        ]),
    ]),
])

tab_general =  dbc.InputGroup([
                    dcc.Dropdown(['No Sequential Scan', 'No Index Scan', 'No Bitmap Scan'],style={'width': "100%"},multi=True),
                    dcc.Dropdown(['No Nested Loop Join', 'No Hash Join', 'No Merge join'],style={'width': "100%"},multi=True),
                    dbc.Button('Generate AQP', id='generate-aqp-general', style={'text-align': 'center'}),
                ])

tab_specific =  dbc.InputGroup([
                    dbc.Button('Generate AQP', id='generate-aqp-specific', style={'text-align': 'center'}),
                ])

# Callback to add or delete query list
@app.callback(
    Output('main-query-list', 'children'),
    [Input('add-query', 'n_clicks'), Input({'type': 'delete-query', 'index': ALL}, 'n_clicks')],
    [State('main-query-list', 'children')],
)
def update_query_list(n1, n2, children):
    # Delete Query
    if n2 and children:
        # Check that trigger is delete query
        if isinstance(ctx.triggered_id, dict) and ctx.triggered_id['type'] == 'delete-query':
            print(f'\ndelete id is : {ctx.triggered_prop_ids}')
            queryid = ctx.triggered_id['index']
            i = 0
            while i < len(children):
                if children[i]['props']['id']['index'] == queryid:
                    children.pop(i)
                    break
                i += 1

    # Add Query
    if n1:
        # Check that trigger is add query
        if isinstance(ctx.triggered_id, str) and ctx.triggered_id == 'add-query':
            print(f'\nadd id is : {ctx.triggered_prop_ids}')
            new_item = dbc.ListGroupItem(
                [
                    dbc.Input(type='text', id={'type': 'query-text', 'index': len(children)}),
                    dbc.Button('Run Query', id={'type': 'run-query', 'index': len(children)}, style={'margin': 8, 'height': '50px'}),
                    dbc.Button('Delete Query', id={'type': 'delete-query', 'index': len(children)}, style={'margin': 8, 'height': '50px'})
                ],
                color='primary', style={'margin': 2}, id={'type': 'query', 'index': len(children)}
            )
            children.append(new_item)
    return children

@app.callback(
    Output('card-content', 'children'),
    [Input('tabs', 'active_tab')]
)
def switch_tab(at):
    if at == 'tab-general':
        return tab_general
    elif at == 'tab-specific':
        return tab_specific
    elif at == 'tab-original':
        return

@app.callback(
    [Output('graph', 'srcDoc'), Output('natural-language', 'children'),
     Output('hit-block', 'children'), Output('read-block', 'children'),
     Output('total-cost', 'children'), Output('buffer-size', 'children')],
    [Input({'type': 'run-query', 'index': ALL}, 'n_clicks')],
    [State('main-query-list', 'children')]
)

def draw_graph(n1, children):
    if n1:
        if isinstance(ctx.triggered_id, dict) and ctx.triggered_id['type'] == 'run-query':
            print(f'\nrun id is : {ctx.triggered_id}')
            queryid = ctx.triggered_id['index']
            for i, child in enumerate(children):
                if child['props']['id']['index'] == queryid:
                    query = child['props']['children'][0]['props']['value']
                    n_query = re.sub(r'\n|\t', " ", query).strip()
                    print(f'the query is : {n_query.upper()}')
                    tables_extracted = extract_tables_from_query(n_query.upper())
                    response = run_query(n_query, tables_extracted)
                    results = response.get_json()  # Extract JSON data from the response
                    if 'error' in results:
                        print(f"Error: {results['error']}")
                    else:
                        print(f"Image URL: {results['data']['imageUrl']}")
                        data = results['data']
                        natural_explanation = data['additionalDetails']['naturalExplanation']
                        natural = natural_explanation
                        natural = convert_html_to_dash(natural)
                        imageurl = data['imageUrl']
                        custom_html = read_graph(imageurl)
                        hit, read, total, size = update_costs(data)
                        return custom_html, natural, hit, read, total, size
    return '', '', '', '', '', ''

# AQP generation callback
@app.callback(
    [Output('graph', 'srcDoc', allow_duplicate=True),
     Output('natural-language', 'children', allow_duplicate=True),
     Output('hit-block', 'children', allow_duplicate=True),
     Output('read-block', 'children', allow_duplicate=True),
     Output('total-cost', 'children', allow_duplicate=True),
     Output('buffer-size', 'children', allow_duplicate=True)],
    Input('generate-aqp-callback', 'n_clicks'),
    State('main-query-list', 'children'),
    prevent_initial_call=True
)
def generate_aqp_specific(n_clicks, query_list):
    if not n_clicks:
        return '', '', '', '', '', ''
        
    try:
        current_query = next((child['props']['children'][0]['props']['value'] 
                            for child in query_list 
                            if child['props']['children'][0]['props'].get('value')), None)
        
        if not current_query:
            raise ValueError("No query found")
            
        n_query = re.sub(r'\n|\t', " ", current_query).strip()
        tables_extracted = extract_tables_from_query(n_query.upper())
            
        selections_response = requests.get('http://localhost:8050/get-selections')
        selections_data = selections_response.json()
        print(selections_data)
        response = run_query(current_query, tables_extracted)
        
        results = response.get_json()
        if 'error' in results:
            raise ValueError(results['error'])
            
        data = results['data']
        natural = convert_html_to_dash(data['additionalDetails']['naturalExplanation'])
        custom_html = read_graph(data['imageUrl'])
        hit, read, total, size = update_costs(data)
        
        return custom_html, natural, hit, read, total, size
            
    except Exception as e:
        print(f"Error generating AQP: {str(e)}")
        return dash.no_update
    
# SERVER CALLS
selections = []
@server.route('/nodeclick', methods=['POST'])
def receive_nodeclick():
    data = request.get_json()
    current_selection = {
        'timestamp': datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
        'node_type': data.get('type'),
        'node_id': data.get('node_id'),
        'what_if': data.get('what_if') 
    }
    
    # Update or append selection
    node_index = next((i for i, s in enumerate(selections) 
                      if s['node_id'] == current_selection['node_id']), -1)
    
    if node_index >= 0:
        selections[node_index] = current_selection
    else:
        selections.append(current_selection)
        
    print(selections)
    return jsonify({'status': 'success'})

@server.route('/get-selections', methods=['GET'])
def get_selections():
    global selections
    response = jsonify(selections)
    selections = []
    return response

if __name__ == '__main__':
    app.run_server(debug=True)