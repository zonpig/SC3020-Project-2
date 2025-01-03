import json
import re

from flask import jsonify

from interface import visualize_query_plan_AQP
from preprocessing import Database, process_query

question_to_planner_option = {
    "What happens if I don't use BitMap Scan at all?": "SET enable_bitmapscan to off;",
    "What happens if I don't use Index Scan at all?": "SET enable_indexscan to off;",
    "What happens if I don't use Sequential Scan at all?": "SET enable_seqscan to off;",
    "What happens if I don't use Nested Loop Join at all?": "SET enable_nestloop to off;",
    "What happens if I don't use Merge Join at all?": "SET enable_mergejoin to off;",
    "What happens if I don't use Hash Join at all?": "SET enable_hashjoin to off;",
}

reset_options = {
    "SET enable_bitmapscan to off;": "RESET enable_bitmapscan;",
    "SET enable_indexscan to off;": "RESET enable_indexscan;",
    "SET enable_seqscan to off;": "RESET enable_seqscan;",
    "SET enable_nestloop to off;": "RESET enable_nestloop;",
    "SET enable_mergejoin to off;": "RESET enable_mergejoin;",
    "SET enable_hashjoin to off;": "RESET enable_hashjoin;",
}

change_scan_mapping = {
    # Sequential Scan
    "replace Sequential Scan with an Index Scan": (
        "SeqScan",
        "IndexScan",
    ),
    "replace Sequential Scan with a BitMap Scan": (
        "SeqScan",
        "BitmapScan",
    ),
    "prevent the use of Sequential Scan": (
        "SeqScan",
        "NoSeqScan",
    ),
    # Index Scan
    "replace Index Scan with a Sequential Scan": (
        "IndexScan",
        "SeqScan",
    ),
    "replace Index Scan with a BitMap Scan": (
        "IndexScan",
        "BitmapScan",
    ),
    "prevent the use of Index Scan": (
        "IndexScan",
        "NoIndexScan",
    ),
    # Bitmap Scan
    "replace BitMap Scan with a Sequential Scan": (
        "BitmapScan",
        "SeqScan",
    ),
    "replace BitMap Scan with an Index Scan": (
        "BitmapScan",
        "IndexScan",
    ),
    "prevent the use of BitMap Scan": (
        "BitmapScan",
        "NoBitmapScan",
    ),
    # Nested Loop Join
    "change Nested Loop Join to a Merge Join": (
        "NestedLoop",
        "MergeJoin",
    ),
    "change Nested Loop Join to a Hash Join": (
        "NestedLoop",
        "HashJoin",
    ),
    "prevent the use of Nested Loop Join": (
        "NestedLoop",
        "NoNestedLoop",
    ),
    # Merge Join
    "change Merge Join to a Nested Loop Join": (
        "MergeJoin",
        "NestedLoop",
    ),
    "change Merge Join to a Hash Join": (
        "MergeJoin",
        "HashJoin",
    ),
    "prevent the use of Merge Join": (
        "MergeJoin",
        "NoMergeJoin",
    ),
    # Hash Join
    "change Hash Join to a Nested Loop Join": (
        "HashJoin",
        "NestedLoop",
    ),
    "change Hash Join to a Merge Join": (
        "HashJoin",
        "MergeJoin",
    ),
    "prevent the use of Hash Join": (
        "HashJoin",
        "NoHashJoin",
    ),
}

scan_join_map_to_plan = {
    "Seq Scan": "SeqScan",
    "Index Scan": "IndexScan",
    "Bitmap Heap Scan": "BitmapScan",
    "Hash Join": "HashJoin",
    "Merge Join": "MergeJoin",
    "Nested Loop": "NestedLoop",
}


def what_if(query: str, questions: list):
    """
    Processes a SQL query with hypothetical scenarios and returns the modified query along with visualization data.

    Args:
        query (str): The original SQL query.
        questions (list): A list of questions or scenarios to apply to the query. Each question can be a dictionary
                          specifying a specific scenario or a string indicating a general scenario.

    Returns:
        flask.Response: A JSON response containing the modified query and, if successful, additional data including
                        a visualization URL, natural explanation, total cost, total blocks, and total nodes. If an
                        error occurs, the response will include an error message.

    Raises:
        KeyError: If a question is not found in the predefined mappings.
        IOError: If there is an issue reading the JSON file containing the query plan.
    """
    planner_option = []
    reset_statements = []

    # Specific Scenario (Tree)
    if isinstance(questions[0], dict):
        changed_hints = {}
        for question in questions:
            change = scan_join_map_to_plan[question["what_if"]]
            changed_hints[question["hint"]] = re.sub(
                r"\b\w+(?=\()", change, question["hint"]
            )
        # Extract hints between /*+ and */
        hints_array = re.findall(r"\b\w+\(.*?\)", query)

        # Replace occurrences of keys in hints_array with their values
        updated_hints_array = [
            changed_hints[hint] if hint in changed_hints else hint
            for hint in hints_array
        ]
        updated_hints_block = "/*+ " + " ".join(updated_hints_array) + " */"
        modified_query = re.sub(
            r"/\*\+.*?\*/", updated_hints_block, query, flags=re.DOTALL
        )

    # General Scenario
    elif questions[0] in question_to_planner_option:
        for question in questions:
            planner_option.append(question_to_planner_option[question])
            reset_statements.append(reset_options[question_to_planner_option[question]])

        planner_option = " ".join(planner_option)

        modified_query = re.sub(r"/\*\+ .*? \*/", f"{planner_option}", query)

        reset_statements = " ".join(reset_statements)

    else:
        # Specific Scenario (Dropdown)
        replacements = []
        # Step 1: Identify necessary replacements based on questions
        for question in questions:
            for description, (old_hint, new_hint) in change_scan_mapping.items():
                if description in question:
                    # Check if the question specifies a single table or a join (two tables)
                    table_match = re.search(r"on table (\w+)", question)
                    join_match = re.search(r"for tables (\w+) and (\w+)", question)

                    if table_match:
                        # Single table hint replacement
                        table_name = table_match.group(1)
                        replacements.append((old_hint, new_hint, table_name, None))
                    elif join_match:
                        # Join hint replacement between two tables
                        table1, table2 = join_match.groups()
                        replacements.append((old_hint, new_hint, table1, table2))
        # Step 2: Apply replacements in one pass
        for old_hint, new_hint, table1, table2 in replacements:
            if table2 is None:
                # Single-table scan replacement
                modified_query = re.sub(
                    rf"\b{old_hint}\({table1}\)", f"{new_hint}({table1})", query
                )
            else:
                # Join replacement for specific table pairs
                modified_query = re.sub(
                    rf"\b{old_hint}\({table1} {table2}\)",
                    f"{new_hint}({table1} {table2})",
                    query,
                )
    result = {"query": modified_query}
    has_error, response = process_query(modified_query)
    if reset_statements:
        connection = Database.get_connection()

        cursor = connection.cursor()

        # Query to get table names from the specified schema
        cursor.execute(reset_statements)

    if has_error:
        result["error"] = response["msg"]
    else:
        json_path = response["plan_data_path"]
        with open(json_path, "r") as json_file:
            plan = json.load(json_file)
        url = visualize_query_plan_AQP(plan)
        image_url = f"{url}"

        result["data"] = {
            "imageUrl": image_url,
            "additionalDetails": {
                "naturalExplanation": response["natural_explain"],
                "totalCost": response["summary_data"]["total_cost"],
                "totalBlocks": response["summary_data"]["total_blocks"],
                "totalNodes": response["summary_data"]["nodes_count"],
            },
        }

    return jsonify(result)
