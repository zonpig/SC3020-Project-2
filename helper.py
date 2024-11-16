import json
import re

from bs4 import BeautifulSoup
from dash import html
from flask import jsonify

from interactive_interface import visualize_query_plan
from preprocessing import Database, process_query


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


def get_postgres_tables():
    """
    Fetch the list of tables from the specified PostgreSQL schema.

    Args:
        schema_name (str): The schema name to fetch tables from.

    Returns:
        list: A list of table names in the given schema.
    """
    try:
        # Replace these values with your PostgreSQL connection details
        connection = Database.get_connection()

        cursor = connection.cursor()

        # Query to get table names from the specified schema
        cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """
        )

        # Fetch all table names
        tables = [row[0].upper() for row in cursor.fetchall()]  # Convert to uppercase

        return tables
    except Exception as e:
        print(f"Error fetching tables: {e}")
        return []


def extract_tables_from_query(sql_query: str):
    # List of valid table names in uppercase

    tables = get_postgres_tables()

    # Find tables in the SQL query
    valid_tables = [table for table in tables if table in sql_query.upper()]

    tokens = sql_query.split()
    table_aliases = {}

    for i, token in enumerate(tokens):
        # Check if the token is a valid table name
        if token in valid_tables:
            # Default alias is the table name itself
            table_aliases[token] = token

            # Check if the next token exists and is not a keyword
            if i + 1 < len(tokens) and tokens[i + 1] not in {
                "FROM",
                "JOIN",
                "WHERE",
                "ON",
                "GROUP",
                "ORDER",
                "LIMIT",
            }:
                alias = tokens[i + 1].strip(",;")
                table_aliases[alias] = token

    return table_aliases


def run_query(query, relations):
    if relations and query:
        query = re.sub(r"\s+", " ", query)

        result = {"query": query}

        has_error, response = process_query(query, relations)
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
                "chartData": response["block_analysis"]["blocks_by_relation"],
                "tableData": response["block_analysis"]["sql_response"],
                "haveCtids": response["block_analysis"]["have_ctids"],
                "isAggregation": response["block_analysis"]["is_aggregation"],
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
