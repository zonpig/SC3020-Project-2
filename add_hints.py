import re
from collections import deque
import logging
import json
import time
from preprocessing import (
    Database,
)


def adding_hints_to_original_query(sql_query):
    # Connect to the PostgreSQL database

    # Use EXPLAIN ANALYZE to get the execution plan with actual runtimes
    explain_query = f"EXPLAIN (ANALYZE, COSTS, SETTINGS, VERBOSE, BUFFERS, SUMMARY, FORMAT JSON) {sql_query}"

    result = {"plan_data_path": None, "hints": None}

    try:
        connection = Database.get_connection()
        cursor = connection.cursor()

        # Execute the EXPLAIN ANALYZE query
        cursor.execute(explain_query)

        # Fetch and format the query execution plan
        qep = cursor.fetchall()[0][0][0].get("Plan")

        print("fetched the QEP!")

        print(qep)

        logging
        logging.basicConfig(
            filename="app.log",
            filemode="w",
            format="%(name)s - %(levelname)s - %(message)s",
        )
        logging.warning("This will get logged to a file")
        logging.warning(f"Plan : {qep}")

        # save plan
        plan_json_name = "plan" + str(time.time()) + ".json"
        with open(plan_json_name, "w") as f:
            json.dump(qep, f)

        # result["plan_data_path"] = plan_json_name
        result["hints"] = get_hints(qep)
        print(result["hints"])

        hints = " ".join(result["hints"])

        # Check if the query already contains "/*+ */"
        if re.search(r"/\*\+ .*? \*/", sql_query):
            # Replace existing hints
            modified_query = re.sub(r"/\*\+ .*? \*/", f"/*+ {hints} */", sql_query)
        else:
            # Add hints at the beginning of the query if not present
            modified_query = f"/*+ {hints} */ {sql_query}"

        print("Query with Hints: ")
        print(modified_query)

        # Close the cursor and connection
        cursor.close()
        connection.close()

        return result["hints"], qep

    except Exception as e:
        print("An error occurred:", e)
        if connection:
            connection.close()
        return None


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
        # "Append": append_natural_explain,
        "Bitmap Heap Scan": bitmap_scan_hint,  # Actually Bitmap
        # "Bitmap Index Scan": bitmap_index_scan_natural_explain,
        # "CTE Scan": cte_natural_explain,
        # "Function Scan": function_scan_natural_explain,
        # "Gather Merge": gather_merge_natural_explain,
        "Hash Join": hash_join_hint,
        "Index Scan": index_scan_hint,
        # "Index Only Scan": index_only_scan_natural_explain,
        "Merge Join": merge_join_hint,
        "Nested Loop": nested_loop_hint,
        "Seq Scan": seq_scan_hint,
        # "SetOp": setop_natural_explain,
        # "Sort": sort_natural_explain,
        # "Subquery Scan": subquery_scan_natural_explain,
        # "Unique": unique_natural_explain,
        # "Values Scan": values_scan_natural_explain,
    }

    if node_type in node_type_to_function.keys():
        return node_type_to_function[node_type](plan)
    else:
        return None


# Scan Hints
def bitmap_scan_hint(plan):
    table = plan["Relation Name"]
    hint = f"BitmapScan({table})"
    print(hint)
    return hint


# def tid_scan_hint(plan):


def index_scan_hint(plan):
    table = plan["Relation Name"]
    hint = f"IndexScan({table})"
    print(hint)
    return hint


# Later
# def index_only_scan_hint(plan):


def seq_scan_hint(plan):
    table = plan["Relation Name"]
    hint = f"SeqScan({table})"
    print(hint)
    return hint


# Join Hints
def nested_loop_hint(plan):
    tables = [re.findall(r"(\w+)\.", item)[0] for item in plan["Output"]]
    hint = f"NestLoop({' '.join(tables)})"
    print(hint)
    return hint


def hash_join_hint(plan):
    tables = re.findall(r"(\w+)\.", plan["Hash Cond"])
    hint = f"HashJoin({' '.join(tables)})"
    print(hint)
    return hint


def merge_join_hint(plan):
    tables = re.findall(r"(\w+)\.", plan["Merge Cond"])
    hint = f"MergeJoin({' '.join(tables)})"
    print(hint)
    return hint


test_query = "SELECT CUSTOMER.C_NAME, NATION.N_NAME FROM CUSTOMER, NATION WHERE CUSTOMER.C_NATIONKEY = NATION.N_NATIONKEY  AND CUSTOMER.C_ACCTBAL <= 5 AND NATION.N_NATIONKEY <= 5"

test_query_2 = "/*+ NestLoop(customer nation) */ SELECT CUSTOMER.C_NAME, NATION.N_NAME FROM CUSTOMER, NATION WHERE CUSTOMER.C_NATIONKEY = NATION.N_NATIONKEY  AND CUSTOMER.C_ACCTBAL <= 5 AND NATION.N_NATIONKEY <= 5"
test_query_3 = "/*+ NoSeqScan(nation) */ SELECT PS_PARTKEY, SUM(PS_SUPPLYCOST * PS_AVAILQTY) AS VALUE  FROM PARTSUPP, SUPPLIER, NATION WHERE PS_SUPPKEY = S_SUPPKEY  AND S_NATIONKEY = N_NATIONKEY AND N_NAME = 'SAUDI ARABIA'  GROUP BY PS_PARTKEY HAVING  SUM(PS_SUPPLYCOST * PS_AVAILQTY) > (SELECT SUM(PS_SUPPLYCOST * PS_AVAILQTY) * 0.0001000000  FROM PARTSUPP, SUPPLIER, NATION WHERE PS_SUPPKEY = S_SUPPKEY AND S_NATIONKEY = N_NATIONKEY AND N_NAME = 'SAUDI ARABIA') ORDER BY VALUE DESC LIMIT 1;"

hints, qep = adding_hints_to_original_query(test_query)


def generate_what_if_questions(hints):
    what_if_questions = []
    what_if_questions_map = {}

    operation_tables = []
    operation_types = set()

    for item in hints:
        # Split the item into the scan type and its parameters
        operation_type, tables = item.split("(")
        tables = tables.strip(")").split()

        operation_types.add(operation_type)
        # Append each operation as a tuple to the list
        operation_tables.append((operation_type, tables))

    operation_type_to_function = {
        "BitmapScan": bitmap_scan_specific_question,  # Actually Bitmap
        "IndexScan": index_scan_specific_question,
        "SeqScan": seq_scan_specific_question,
        "NestLoop": nested_loop_specific_question,
        "MergeJoin": merge_join_specific_question,
        "HashJoin": hash_join_specific_question,
    }

    for idx, operation_table in enumerate(operation_tables):
        operation_type, tables = operation_table
        if operation_type in operation_type_to_function.keys():
            what_if_questions.extend(operation_type_to_function[operation_type](tables))
            what_if_questions_map[hints[idx]] = operation_type_to_function[
                operation_type
            ](tables)
        else:
            continue

    for operation_type in operation_types:
        if operation_type == "BitmapScan":
            what_if_questions.append(bitmap_scan_general_question())
        elif operation_type == "IndexScan":
            what_if_questions.append(index_scan_general_question())
        elif operation_type == "SeqScan":
            what_if_questions.append(seq_scan_general_question())
        elif operation_type == "NestLoop":
            what_if_questions.append(nested_loop_general_question())
        elif operation_type == "MergeJoin":
            what_if_questions.append(merge_join_general_question())
        elif operation_type == "HashJoin":
            what_if_questions.append(hash_join_general_question())

    print(what_if_questions_map)

    return what_if_questions


# Scan What-if Questions
def bitmap_scan_specific_question(table):
    questions = [
        f"What happens if I replace BitMap Scan with a Sequential Scan on table {table[0]}?",
        f"What happens if I replace BitMap Scan with a Index Scan on table {table[0]}?",
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
        f"What happens if I change Nested Loop Join to a Hash Join for table {table_a} and {table_b}?",
        f"What happens if I change Nested Loop Join to a Merge Join for table {table_a} and {table_b}",
        f"What happens if I prevent the use of Nested Loop Join for table {table_a} and {table_b}?",
    ]
    return questions


def hash_join_specific_question(tables):
    table_a, table_b = tables
    questions = [
        f"What happens if I change Hash Join to a Nested Loop Join for table {table_a} and {table_b}?",
        f"What happens if I change Hash Join to a Merge Join for table {table_a} and {table_b}?",
        f"What happens if I prevent the use of Hash Join for table {table_a} and {table_b}?",
    ]
    return questions


def merge_join_specific_question(tables):
    table_a, table_b = tables
    questions = [
        f"What happens if I change Merge Join to a Nested Loop Join of table {table_a} and {table_b} ?",
        f"What happens if I change Merge Join to a Hash Join of table {table_a} and {table_b} ?",
        f"What happens if I prevent the use of Merge Join for table {table_a} and {table_b}?",
    ]
    return questions


def nested_loop_general_question():
    return "What happens if I don't use Nested Loop Join at all?"


def hash_join_general_question():
    return "What happens if I don't use Hash Join at all?"


def merge_join_general_question():
    return "What happens if I don't use Merge Join at all?"


test = ["IndexScan(nation)", "SeqScan(customer)", "NestLoop(customer nation)"]

print(generate_what_if_questions(test))

[
    "What happens if I change the Index Scan of table nation to a Sequential Scan?",
    "What happens if I change the Index Scan of table nation to a BitMap Scan?",
    "What happens if I prevent the use of Index Scan for table nation?",
    "What happens if I change the Sequential Scan of table customer to an Index Scan?",
    "What happens if I change the Sequential Scan of table customer to a BitMap Scan?",
    "What happens if I prevent the use of Sequential Scan for table customer?",
    "What happens if I change the Nested Loop Join of table customer and nation to a Hash Join?",
    "What happens if I change the Nested Loop Join of table customer and nation to a Merge Join?",
    "What happens if I prevent the use of Nested Loop Join for table customer and nation?",
    "What happens if I don't use Sequential Scan at all?",
    "What happens if I don't use Index Scan at all?",
    "What happens if I don't use Nested Loop Join at all?",
]


def process_whatif_query(sql_query, query_execution_plan):
    modified_query = sql_query
    modified_plan = query_execution_plan
    return modified_query, modified_plan


{
    "IndexScan(nation)": [
        "What happens if I replace Index Scan with a Sequential Scan on table nation?",
        "What happens if I replace Index Scan with a BitMap Scan on table nation?",
        "What happens if I prevent the use of Index Scan for table nation?",
    ],
    "SeqScan(customer)": [
        "What happens if I replace Sequential Scan with an Index Scan on table customer?",
        "What happens if I replace Sequential Scan with a BitMap Scan on table customer?",
        "What happens if I prevent the use of Sequential Scan for table customer?",
    ],
    "NestLoop(customer nation)": [
        "What happens if I change Nested Loop Join to Hash Join for table customer and nation?",
        "What happens if I change Nested Loop Join to Merge Join for table customer and nation",
        "What happens if I prevent the use of Nested Loop Join for table customer and nation?",
    ],
}
[
    "What happens if I replace Index Scan with a Sequential Scan on table nation?",
    "What happens if I replace Index Scan with a BitMap Scan on table nation?",
    "What happens if I prevent the use of Index Scan for table nation?",
    "What happens if I replace Sequential Scan with an Index Scan on table customer?",
    "What happens if I replace Sequential Scan with a BitMap Scan on table customer?",
    "What happens if I prevent the use of Sequential Scan for table customer?",
    "What happens if I change Nested Loop Join to Hash Join for table customer and nation?",
    "What happens if I change Nested Loop Join to Merge Join for table customer and nation",
    "What happens if I prevent the use of Nested Loop Join for table customer and nation?",
    "What happens if I don't use Nested Loop Join at all?",
    "What happens if I don't use Sequential Scan at all?",
    "What happens if I don't use Index Scan at all?",
]
