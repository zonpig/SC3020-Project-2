import re
from preprocessing import process_query, Database
from interactive_interface import visualize_query_plan
from flask import jsonify
from psycopg2 import OperationalError, ProgrammingError
import json

question_to_planner_option = {
    "What happens if I don't use BitMap Scan at all?": "SET enable_bitmapscan to off;",  # Actually Bitmap
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
    "replace Nested Loop Join with a Merge Join": (
        "NestedLoop",
        "MergeJoin",
    ),
    "replace Nested Loop Join with a Hash Join": (
        "NestedLoop",
        "HashJoin",
    ),
    "prevent the use of Nested Loop Join": (
        "NestedLoop",
        "NoNestedLoop",
    ),
    # Merge Join
    "replace Merge Join with a Nested Loop Join": (
        "MergeJoin",
        "NestedLoop",
    ),
    "replace Merge Join with a Hash Join": (
        "MergeJoin",
        "HashJoin",
    ),
    "prevent the use of Merge Join": (
        "MergeJoin",
        "NoMergeJoin",
    ),
    # Hash Join
    "replace Hash Join with a Nested Loop Join": (
        "HashJoin",
        "NestedLoop",
    ),
    "replace Hash Join with a Merge Join": (
        "HashJoin",
        "MergeJoin",
    ),
    "prevent the use of Hash Join": (
        "HashJoin",
        "NoHashJoin",
    ),
}


def what_if(query, relations, questions):
    scenario = None
    # General Scenario
    if questions[0] in question_to_planner_option:
        scenario = "General"
        planner_option = []
        reset_statements = []
        for question in questions:
            planner_option.append(question_to_planner_option[question])
            reset_statements.append(reset_options[question_to_planner_option[question]])

        planner_option = " ".join(planner_option)

        modified_query = re.sub(r"/\*\+ .*? \*/", f"{planner_option}", query)
        print(modified_query)

        reset_statements = " ".join(reset_statements)
        print(reset_statements)

    else:
        # Specific Scenario (Tree)

        # Specific Scenario (Dropdown)
        replacements = []

        # Step 1: Identify necessary replacements based on questions
        for question in questions:
            for description, (old_hint, new_hint) in change_scan_mapping.items():
                if description in question:
                    print(question)
                    print(description)
                    # Check if the question specifies a single table or a join (two tables)
                    table_match = re.search(r"for table (\w+)", question)
                    join_match = re.search(r"for tables (\w+) and (\w+)", question)

                    if table_match:
                        # Single table hint replacement
                        table_name = table_match.group(1)
                        replacements.append((old_hint, new_hint, table_name, None))
                    elif join_match:
                        # Join hint replacement between two tables
                        table1, table2 = join_match.groups()
                        replacements.append((old_hint, new_hint, table1, table2))
        print(replacements)
        # Step 2: Apply replacements in one pass
        for old_hint, new_hint, table1, table2 in replacements:
            if table2 is None:
                # Single-table scan replacement
                modified_query = re.sub(
                    rf"\b{old_hint}\({table1}\)", f"{new_hint}({table1})", query
                )
                print(modified_query)
            else:
                # Join replacement for specific table pairs
                modified_query = re.sub(
                    rf"\b{old_hint}\({table1} {table2}\)",
                    f"{new_hint}({table1} {table2})",
                    query,
                )

    if scenario == "General":
        try:
            connection = Database.get_connection()

            with connection.cursor() as cur:
                try:
                    cur.execute(planner_option)
                    result = {"query": modified_query}
                    print("test", modified_query)
                    has_error, response = process_query(
                        query, relations
                    )  # Define this function based on your needs'
                    cur.execute(reset_statements)
                except ProgrammingError as e:
                    print(e)
                    cur.execute("ROLLBACK;")
                    return True, {"msg": "Invalid SQL query!"}
        except OperationalError:
            return True, {"msg": "Database connection error!"}

    else:
        result = {"query": modified_query}
        print("test", modified_query)
        has_error, response = process_query(
            modified_query, relations
        )  # Define this function based on your needs
    if has_error:
        result["error"] = response["msg"]
    else:
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
            "additionalDetails": {
                "naturalExplanation": response["natural_explain"],
                "totalCost": response["summary_data"]["total_cost"],
                "totalBlocks": response["summary_data"]["total_blocks"],
                "totalNodes": response["summary_data"]["nodes_count"],
            },
        }

    return jsonify(result)


query = "/*+ SeqScan(nation) SeqScan(customer) HashJoin(customer nation) */ SELECT CUSTOMER.C_NAME, NATION.N_NAME FROM CUSTOMER, NATION WHERE CUSTOMER.C_NATIONKEY = NATION.N_NATIONKEY  AND CUSTOMER.C_ACCTBAL <= 5 AND NATION.N_NATIONKEY <= 5;"

# what_if(
#     query,
#     {"nation":"nation", "customer":"customer"},",
#     [
#         "What happens if I prevent the use of Sequential Scan for table customer?",
#         "What happens if I prevent the use of Hash Join for tables customer and nation?",
#     ],
# )
