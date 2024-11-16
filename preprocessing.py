# Code for reading inputs and any preprocessing to make your algorithm work
import json
import logging
import re
import time
from collections import deque
from typing import Tuple

import psycopg2
from psycopg2 import OperationalError, ProgrammingError


####################################### Database Connection #######################################
class Database:
    connection = None
    database = "TPC-H"  # Default database

    @classmethod
    def set_database(cls, new_database):
        """
        Updates the database name and resets the connection.
        """
        cls.database = new_database
        # Close the existing connection if there is one
        if cls.connection is not None:
            cls.connection.close()
            cls.connection = None  # Reset connection to ensure new one is created

    @classmethod
    def get_connection(cls):
        """
        Returns a connection to the current database.
        """
        if cls.connection is None:
            cls.connection = psycopg2.connect(
                host="localhost",
                database=cls.database,
                user="postgres",
                password="password",
                port="5433",
            )
        return cls.connection


####################################### Database Functions #######################################
def get_postgres_schemas():
    try:
        connection = Database.get_connection()

        cursor = connection.cursor()

        # Query for schemas
        cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        schemas = [row[0] for row in cursor.fetchall()]

        return schemas
    except Exception as e:
        print("Error retrieving schemas:", e)
        return []


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


####################################### Core Function #######################################
"""
Main Function : process_query

>> Process query plan for the given user query.

>> Returns:
    - error boolean: True if error, False otherwise
    - result dictionary: contains message if error, else contains plan_data, summary_data and natural_explain
"""


def process_query(user_query: str) -> Tuple[bool, dict]:
    """
    Processes a SQL query by executing it, analyzing the query plan, and generating various insights.

    Args:
        user_query (str): The SQL query provided by the user.
    Returns:
        error boolean: True if error, False otherwise
        result dictionary: contains message if error, else contains plan_data, summary_data, natural_explain, block_analysis, specific_what_if, general_what_if, and query_with_hints

    Raises:
        OperationalError: If there is an issue connecting to the database.
        Exception: For any other exceptions that occur during processing.
    """
    result = {
        "plan_data_path": None,
        "summary_data": None,
        "natural_explain": None,
        "specific_what_if": None,
        "general_what_if": None,
        "query_with_hints": None,
    }

    try:
        connection = Database.get_connection()

        # Check for SET statements
        set_statements = []
        main_query = None  # Initialize as None to avoid overwriting

        # Split the user query by semicolon
        queries = user_query.split(";")

        for query in queries:
            query = query.strip()
            if not query:  # Skip empty queries resulting from split
                continue
            if query.upper().startswith("SET"):
                set_statements.append(query)
            else:
                main_query = query  # Assign the last non-SET query as main_query
        # Execute SET statements
        with connection.cursor() as cur:
            for set_statement in set_statements:
                try:
                    cur.execute(set_statement)
                except ProgrammingError as e:
                    print(e)
                    cur.execute("ROLLBACK;")
                    return True, {"msg": f"Error in SET statement: {set_statement}"}

        # Get base query plan
        with connection.cursor() as cur:
            try:
                print(f"Executing main query: {main_query}")
                # Execute query and get results
                explain_query_str = f"EXPLAIN (ANALYZE, COSTS, SETTINGS, VERBOSE, BUFFERS, SUMMARY, FORMAT JSON) {main_query};"
                cur.execute(explain_query_str)
                plan = cur.fetchall()[0][0][0].get("Plan")
            except ProgrammingError as e:
                print(e)
                cur.execute("ROLLBACK;")
                return True, {"msg": "Invalid SQL query!"}

        # logging
        logging.basicConfig(
            filename="app.log",
            filemode="w",
            format="%(name)s - %(levelname)s - %(message)s",
        )
        logging.warning("This will get logged to a file")
        logging.warning(f"Plan : {plan}")

        # save plan
        plan_json_name = f"static/plan_{int(time.time())}_{hash(main_query)}.json"
        with open(plan_json_name, "w") as f:
            json.dump(plan, f)
        result["plan_data_path"] = plan_json_name
        # parse results for summary for plan
        result["summary_data"] = get_plan_summary(plan)
        # get natural explanation for plan
        result["natural_explain"] = get_natural_explanation(plan)
        # get hints for query
        result["hints"] = get_hints(plan)
        hints = " ".join(result["hints"])
        # Add hints at the beginning of the query
        modified_query = f"/*+ {hints} */ {user_query}"
        result["query_with_hints"] = modified_query
        if not set_statements:
            specific_what_if, general_what_if = generate_what_if_questions(
                result["hints"]
            )
            result["specific_what_if"] = specific_what_if
            result["general_what_if"] = general_what_if

    except OperationalError:
        return True, {
            "msg": "An error has occurred: Failed to connect to the database! Please ensure that the database is running."
        }
    except Exception as e:
        return True, {"msg": f"An error has occurred: {repr(e)}"}

    return False, result


####################################### Helper Functions #######################################


#######################################Plan Summary#######################################
def get_plan_summary(plan):
    """
    Generate a summary of the given execution plan.

    Args:
        plan (dict): A dictionary representing the execution plan.

    Returns:
        dict: A summary of the execution plan containing:
            - total_cost (float): The total cost of the plan.
            - total_blocks (dict): A dictionary with:
                - hit_blocks (int): The number of shared hit blocks.
                - read_blocks (int): The number of shared read blocks.
            - nodes_count (int): The total number of nodes in the plan.
    """
    summary = {
        "total_cost": plan["Total Cost"],
        "total_blocks": {
            "hit_blocks": plan["Shared Hit Blocks"],
            "read_blocks": plan["Shared Read Blocks"],
        },
        "nodes_count": 0,
    }
    q = deque([plan])
    while q:
        node = q.popleft()
        summary["nodes_count"] += 1
        if "Plans" in node:
            for child in node["Plans"]:
                q.append(child)
    return summary


####################################### Natural Explanation #######################################
def get_natural_explanation(plan):
    """
    Generates a natural language explanation for a given plan.

    This function takes a hierarchical plan structure and produces a list of natural language explanations
    for each node in the plan. The explanations are generated in a bottom-up manner, starting from the
    leaf nodes and moving up to the root node.

    Args:
        plan (dict): A dictionary representing the hierarchical plan. Each node in the plan may contain
                     a "Plans" key, which is a list of child nodes.

    Returns:
        list: A list of natural language explanations for each node in the plan, ordered from the leaf
              nodes to the root node.
    """
    natural_explanation = []
    q = deque([plan])
    while q:
        node = q.popleft()
        natural_explanation.append(natural_explain(node))
        if "Plans" in node:
            for child in node["Plans"]:
                q.append(child)
    return natural_explanation[::-1]


def natural_explain(plan):
    node_type = plan["Node Type"]

    node_type_to_function = {
        "Aggregate": aggregate_natural_explain,
        "Append": append_natural_explain,
        "Bitmap Heap Scan": bitmap_heap_scan_natural_explain,
        "Bitmap Index Scan": bitmap_index_scan_natural_explain,
        "CTE Scan": cte_natural_explain,
        "Function Scan": function_scan_natural_explain,
        "Gather": gather_natural_explain,
        "Gather Merge": gather_merge_natural_explain,
        "Group": group_natural_explain,
        "Hash": hash_natural_explain,
        "Hash Join": hash_join_natural_explain,
        "Index Scan": index_scan_natural_explain,
        "Index Only Scan": index_only_scan_natural_explain,
        "Limit": limit_natural_explain,
        "Materialize": materialize_natural_explain,
        "Memoize": memoize_natural_explain,
        "Merge Join": merge_join_natural_explain,
        "Nested Loop": nested_loop_natural_explain,
        "Seq Scan": seq_scan_natural_explain,
        "SetOp": setop_natural_explain,
        "Sort": sort_natural_explain,
        "Subquery Scan": subquery_scan_natural_explain,
        "Unique": unique_natural_explain,
        "Values Scan": values_scan_natural_explain,
    }

    if node_type in node_type_to_function.keys():
        return node_type_to_function[node_type](plan)
    else:
        return node_type


bold = {"START": "<b>", "END": "</b>"}


def bold_string(string):
    return bold["START"] + string + bold["END"]


def aggregate_natural_explain(plan):
    strategy = plan["Strategy"]
    if strategy == "Plain":
        return f"Basic {bold_string('Aggregate')} operation is performed on the result."
    elif strategy == "Hashed":
        result = f"{bold_string('Aggregate')} operation involves hashing all rows based on the following key(s): "
        for key in plan["Group Key"]:
            result += bold_string(key.replace("::text", "")) + ", "
        result += f"and then {bold_string('aggregating')} the results into bucket(s) according to the hashed key."
        return result
    elif strategy == "Sorted":
        result = f"{bold_string('Aggregate')} operation is performed on the rows based on their keys."
        if "Group Key" in plan:
            result += f" The {bold_string('aggregated')} key(s) are: "
            for key in plan["Group Key"]:
                result += bold_string(key) + ","
            result = result[:-1] + "."
        if "Filter" in plan:
            result += " The rows are also filtered by " + bold_string(
                plan["Filter"].replace("::text", "")
            )
            result += "."
        return result
    else:
        return "Aggregation is performed."


def append_natural_explain(plan):
    result = f"The {bold_string('Append')} operation aggregates multiple sub-operations, combining all returned rows into a single result set."
    return result


def bitmap_heap_scan_natural_explain(plan):
    result = f"With the result from the previous {bold_string('Bitmap Index Scan')}, {bold_string('Bitmap Heap Scan')} is performed on {bold_string(plan['Relation Name'])} table. To get results matching the condition {bold_string(plan['Recheck Cond'])} which is used to create the Bitmap."
    return result


def bitmap_index_scan_natural_explain(plan):
    result = f"{bold_string('Bitmap Index Scan')} is performed on {bold_string(plan['Index Name'])} with index condition of {bold_string(plan['Index Cond'])} to create a Bitmap."
    return result


def cte_natural_explain(plan):
    result = f"A {bold_string('CTE scan')} operation is performed on the table {bold_string(str(plan['CTE Name']))} which is stored in memory "
    if "Index Cond" in plan:
        result += f" with the condition(s) {bold_string(plan['Index Cond'].replace('::text', ''))}"
    if "Filter" in plan:
        result += f" the result is then filtered by {bold_string(plan['Filter'].replace('::text', ''))}"
    result += "."
    return result


def function_scan_natural_explain(plan):
    return "The function {} is run and returns all the recordset(s) that it created.".format(
        bold_string(plan["Function Name"])
    )


def gather_natural_explain(plan):
    result = f"{bold_string('Gather')} operation is performed on the results from parallel sub-operations. The results order is {bold_string('Not')} preserved unlike {bold_string('Gather Merge')}."
    return result


def gather_merge_natural_explain(plan):
    result = f"{bold_string('Gather Merge')} operation is performed on the results from parallel sub-operations. The results {bold_string('Sorted')} order is preserved."
    return result


def group_natural_explain(plan):
    result = f"The result from the previous operation is {bold_string('grouped')} by the following key(s): "
    for i, key in enumerate(plan["Group Key"]):
        result += bold_string(key.replace("::text", ""))
        if i == len(plan["Group Key"]) - 1:
            result += "."
        else:
            result += ", "
    return result


def hash_natural_explain(plan):
    result = f"{bold_string('Hash')} function is used to make a memory {bold_string('hash')} using the table rows."
    return result


def hash_join_natural_explain(plan):
    result = f"The result from previous operation is joined using {bold_string('Hash')} {bold_string(plan['Join Type'])} {bold_string('Join')}"
    if "Hash Cond" in plan:
        result += " on the condition: {}".format(
            bold_string(plan["Hash Cond"].replace("::text", ""))
        )
    result += "."
    return result


def index_scan_natural_explain(plan):
    result = ""
    result += (
        f"{bold_string('Index Scan')} operation is performed using "
        + bold_string(plan["Index Name"])
        + " index table "
    )
    if "Index Cond" in plan:
        result += " with the following condition(s): " + bold_string(
            plan["Index Cond"].replace("::text", "")
        )
    result += ", and the {} table and fetches rows that matches the conditions.".format(
        bold_string(plan["Relation Name"])
    )

    if "Filter" in plan:
        result += (
            " The result is then filtered by "
            + bold_string(plan["Filter"].replace("::text", ""))
            + "."
        )
    return result


def index_only_scan_natural_explain(plan):
    result = ""
    result += (
        f"An {bold_string('Index Scan')} operation is done using "
        + bold_string(plan["Index Name"])
        + " index table"
    )
    if "Index Cond" in plan:
        result += " with the condition(s) " + bold_string(
            plan["Index Cond"].replace("::text", "")
        )
    result += ". Matches are then returned as the result."
    if "Filter" in plan:
        result += (
            " The result is finally filtered by: "
            + bold_string(plan["Filter"].replace("::text", ""))
            + "."
        )
    return result


def limit_natural_explain(plan):
    result = f"A scan is performed with a {bold_string('limit')} of {plan['Plan Rows']} entries."
    return result


def materialize_natural_explain(plan):
    result = f"{bold_string('Materialize')} operation is performed. This means the results of previous operation(s) are stored in physical memory/disk for faster access."
    return result


def memoize_natural_explain(plan):
    result = f"The previous sub-operation result is then {bold_string('Memoized')}. This means that the result is cached with cache key of {bold_string(plan['Cache Key'])}."
    return result


def merge_join_natural_explain(plan):
    result = f"{bold_string('Merge Join')} operation is performed on results from sub-operations"

    if "Merge Cond" in plan:
        result += " on the condition " + bold_string(
            plan["Merge Cond"].replace("::text", "")
        )

    if "Join Type" == "Semi":
        result += " but only the rows from the left relation is returned as the result"

    result += "."
    return result


def nested_loop_natural_explain(plan):
    result = f"{bold_string('Nested Loop')} is performed to join results between the scans of the suboperations."
    return result


def seq_scan_natural_explain(plan):
    sentence = f"{bold_string('Sequential Scan')} operation is performed on relation "
    if "Relation Name" in plan:
        sentence += bold_string(plan["Relation Name"])
    if "Alias" in plan:
        if plan["Relation Name"] != plan["Alias"]:
            sentence += " with the alias of {}".format(plan["Alias"])
    if "Filter" in plan:
        sentence += " and filtered by {}".format(plan["Filter"].replace("::text", ""))
    sentence += "."

    return sentence


def setop_natural_explain(plan):
    result = "Results are returned base on the"
    cmd_name = bold_string(str(plan["Command"]))
    if cmd_name == "Except" or cmd_name == "Except All":
        result += "differences "
    else:
        result += "similarities "
    result += (
        "between the two previously scanned tables using the {} operation.".format(
            bold_string(plan["Node Type"])
        )
    )

    return result


def sort_natural_explain(plan):
    result = f"The result is {bold_string('Sorted')} using the attribute "
    if "DESC" in plan["Sort Key"]:
        result += (
            bold_string(str(plan["Sort Key"].replace("DESC", "")))
            + " in descending order of "
        )
    elif "INC" in plan["Sort Key"]:
        result += (
            bold_string(str(plan["Sort Key"].replace("INC", "")))
            + " in ascending order of "
        )
    else:
        result += bold_string(str(plan["Sort Key"]))
    result += "."
    return result


def subquery_scan_natural_explain(plan):
    result = f"{bold_string('Subquery scan')} operation is performed on results from sub-operations without any changes."
    return result


def unique_natural_explain(plan):
    result = f"A scan is performed on previous results to remove {bold_string('un-unique')} values."
    return result


def values_scan_natural_explain(plan):
    result = f"A {bold_string('Values Scan')} operation is performed using the values given in query."
    return result


####################################### Hint Function #######################################
def get_hints(qep):
    hints = []
    q = deque([qep])
    while q:
        node = q.popleft()
        hints.append(produce_hints(node))
        if "Plans" in node:
            for child in node["Plans"]:
                q.append(child)
    hints = [hint for hint in hints if hint is not None]
    return hints[::-1]


def produce_hints(plan):
    node_type = plan["Node Type"]

    node_type_to_function = {
        "Bitmap Heap Scan": bitmap_scan_hint,
        "Hash Join": hash_join_hint,
        "Index Scan": index_scan_hint,
        "Merge Join": merge_join_hint,
        "Nested Loop": nested_loop_hint,
        "Seq Scan": seq_scan_hint,
    }

    if node_type in node_type_to_function.keys():
        return node_type_to_function[node_type](plan)
    else:
        return None


def generate_what_if_questions(hints):
    what_if_specific_questions = []
    what_if_general_questions = []

    operation_tables = []
    operation_types = set()

    for item in hints:
        # Split the item into the scan type and its parameters
        operation_type, tables = item.split("(")
        tables = tables.strip(")").split()

        operation_types.add(operation_type)
        # Append each operation as a tuple to the list
        operation_tables.append((operation_type, tables))

    operation_type_to_specific_function = {
        "BitmapScan": bitmap_scan_specific_question,
        "IndexScan": index_scan_specific_question,
        "SeqScan": seq_scan_specific_question,
        "NestLoop": nested_loop_specific_question,
        "MergeJoin": merge_join_specific_question,
        "HashJoin": hash_join_specific_question,
    }

    for operation_table in operation_tables:
        operation_type, tables = operation_table
        if operation_type in operation_type_to_specific_function.keys():
            what_if_specific_questions.extend(
                operation_type_to_specific_function[operation_type](tables)
            )

    operation_type_to_general_function = {
        "BitmapScan": bitmap_scan_general_question,
        "IndexScan": index_scan_general_question,
        "SeqScan": seq_scan_general_question,
        "NestLoop": nested_loop_general_question,
        "MergeJoin": merge_join_general_question,
        "HashJoin": hash_join_general_question,
    }

    for operation_type in operation_types:
        what_if_general_questions.append(
            operation_type_to_general_function[operation_type]()
        )

    return what_if_specific_questions, what_if_general_questions


# Scan Hints
def bitmap_scan_hint(plan):
    table = plan["Relation Name"]
    hint = f"BitmapScan({table})"
    return hint


def index_scan_hint(plan):
    table = plan["Relation Name"]
    hint = f"IndexScan({table})"
    return hint


def seq_scan_hint(plan):
    table = plan["Relation Name"]
    hint = f"SeqScan({table})"
    return hint


# Join Hints
def nested_loop_hint(plan):
    tables = [re.findall(r"(\w+)\.", item)[0] for item in plan["Output"]]
    hint = f"NestLoop({' '.join(tables)})"
    return hint


def hash_join_hint(plan):
    tables = re.findall(r"(\w+)\.", plan["Hash Cond"])
    hint = f"HashJoin({' '.join(tables)})"
    return hint


def merge_join_hint(plan):
    tables = re.findall(r"(\w+)\.", plan["Merge Cond"])
    hint = f"MergeJoin({' '.join(tables)})"
    return hint


# Scan What-if Questions
def bitmap_scan_specific_question(table):
    questions = [
        f"What happens if I replace BitMap Scan with a Sequential Scan on table {table[0]}?",
        f"What happens if I replace BitMap Scan with an Index Scan on table {table[0]}?",
        f"What happens if I prevent the use of BitMap Scan for table {table[0]}?",
    ]
    return questions


def index_scan_specific_question(table):
    questions = [
        f"What happens if I replace Index Scan with a Sequential Scan on table {table[0]}?",
        f"What happens if I replace Index Scan with a BitMap Scan on table {table[0]}?",
        f"What happens if I prevent the use of Index Scan for table {table[0]}?",
    ]
    return questions


def seq_scan_specific_question(table):
    questions = [
        f"What happens if I replace Sequential Scan with an Index Scan on table {table[0]}?",
        f"What happens if I replace Sequential Scan with a BitMap Scan on table {table[0]}?",
        f"What happens if I prevent the use of Sequential Scan for table {table[0]}?",
    ]
    return questions


def bitmap_scan_general_question():
    return "What happens if I don't use BitMap Scan at all?"


def index_scan_general_question():
    return "What happens if I don't use Index Scan at all?"


def seq_scan_general_question():
    return "What happens if I don't use Sequential Scan at all?"


# Join What-if Questions
def nested_loop_specific_question(tables):
    table_a, table_b = tables
    questions = [
        f"What happens if I change Nested Loop Join to a Hash Join for tables {table_a} and {table_b}?",
        f"What happens if I change Nested Loop Join to a Merge Join for tables {table_a} and {table_b}",
        f"What happens if I prevent the use of Nested Loop Join for tables {table_a} and {table_b}?",
    ]
    return questions


def hash_join_specific_question(tables):
    table_a, table_b = tables
    questions = [
        f"What happens if I change Hash Join to a Nested Loop Join for tables {table_a} and {table_b}?",
        f"What happens if I change Hash Join to a Merge Join for tables {table_a} and {table_b}?",
        f"What happens if I prevent the use of Hash Join for tables {table_a} and {table_b}?",
    ]
    return questions


def merge_join_specific_question(tables):
    table_a, table_b = tables
    questions = [
        f"What happens if I change Merge Join to a Nested Loop Join of tables {table_a} and {table_b} ?",
        f"What happens if I change Merge Join to a Hash Join of tables {table_a} and {table_b} ?",
        f"What happens if I prevent the use of Merge Join for tables {table_a} and {table_b}?",
    ]
    return questions


def nested_loop_general_question():
    return "What happens if I don't use Nested Loop Join at all?"


def hash_join_general_question():
    return "What happens if I don't use Hash Join at all?"


def merge_join_general_question():
    return "What happens if I don't use Merge Join at all?"
