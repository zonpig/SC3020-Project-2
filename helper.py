import json
import re
from preprocessing import process_query
from interactive_interface import visualize_query_plan
from flask import jsonify
from bs4 import BeautifulSoup
from dash import html


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


def extract_tables_from_query(sql_query: str):
    # List of valid table names in uppercase
    valid_tables = [
        "REGION",
        "NATION",
        "PART",
        "SUPPLIER",
        "PARTSUPP",
        "CUSTOMER",
        "ORDERS",
        "LINEITEM",
    ]

    tokens = sql_query.split()
    table_aliases = {}

    current_alias = None

    for i in range(len(tokens)):
        token = tokens[i].strip()
        if token in valid_tables:
            # If the token is FROM or JOIN, set the next token as the value
            next_token = tokens[i + 1].strip()

            if len(next_token) == 1:
                # If the next token is a single character, use it as the alias key
                current_alias = next_token
                table_aliases[current_alias] = token
                i += 1  # Skip the next token as it has been processed
            else:
                # Otherwise, use the next token as the key itself
                current_alias = token
                table_aliases[current_alias] = token

    return table_aliases


def run_query(query, relations):
    if relations and query:
        query = re.sub(r"\s+", " ", query)

        result = {"query": query}

        has_error, response = process_query(
            query, relations
        )  # Define this function based on your needs
        if has_error:
            result["error"] = response["msg"]
        else:
            specific_what_if = response["specific_what_if"]
            general_what_if = response["general_what_if"]
            json_path = response["plan_data_path"]
            with open(json_path, "r") as json_file:
                plan = json.load(json_file)
            url = visualize_query_plan(plan)  # Define this function based on your needs
            image_url = f"{url}"

            result["data"] = {
                "chartData": response["block_analysis"]["blocks_by_relation"],
                "tableData": response["block_analysis"]["sql_response"],
                "haveCtids": response["block_analysis"]["have_ctids"],
                "isAggregation": response["block_analysis"]["is_aggregation"],
                "imageUrl": image_url,
                'hints': response['hints'],
                'modifiedQuery': response['query_with_hints'],
                'generalWhatif': response['general_what_if'],
                'specificWhatif': response['specific_what_if'],
                "additionalDetails": {
                    "naturalExplanation": response["natural_explain"],
                    "totalCost": response["summary_data"]["total_cost"],
                    "totalBlocks": response["summary_data"]["total_blocks"],
                    "totalNodes": response["summary_data"]["nodes_count"],
                },
            }

        return specific_what_if, general_what_if, jsonify(result)
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
