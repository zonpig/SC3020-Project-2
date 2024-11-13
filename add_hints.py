import re
from collections import deque

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

        # logging
        # logging.basicConfig(
        #     filename="app.log",
        #     filemode="w",
        #     format="%(name)s - %(levelname)s - %(message)s",
        # )
        # logging.warning("This will get logged to a file")
        # logging.warning(f"Plan : {qep}")

        # # save plan
        # plan_json_name = "plan" + str(time.time()) + ".json"
        # with open(plan_json_name, "w") as f:
        #     json.dump(qep, f)

        # result["plan_data_path"] = plan_json_name
        result["hints"] = get_hints(qep)

        modified_query = re.sub(
            r"/\*\+ .*? \*/", f"/* {' '.join(result['hints'])} */", sql_query
        )
        print("Query with Hints: ")
        print(modified_query)

        # Close the cursor and connection
        cursor.close()
        connection.close()

        return qep

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
        # "Aggregate": aggregate_natural_explain,
        # "Append": append_natural_explain,
        "Bitmap Heap Scan": bitmap_scan_hint,  # Actually Bitmap
        # "Bitmap Index Scan": bitmap_index_scan_natural_explain,
        # "CTE Scan": cte_natural_explain,
        # "Function Scan": function_scan_natural_explain,
        # "Gather": gather_natural_explain,
        # "Gather Merge": gather_merge_natural_explain,
        # "Group": group_natural_explain,
        # "Hash": hash_natural_explain,
        "Hash Join": hash_join_hint,
        "Index Scan": index_scan_hint,
        # "Index Only Scan": index_only_scan_natural_explain,
        # "Limit": limit_natural_explain,
        # "Materialize": materialize_natural_explain,
        # "Memoize": memoize_natural_explain,
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
    hint = f"NestedLoop({' '.join(tables)})"
    print(hint)


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


test_query = "/*+ NestLoop(customer nation) */ SELECT CUSTOMER.C_NAME, NATION.N_NAME FROM CUSTOMER, NATION WHERE CUSTOMER.C_NATIONKEY = NATION.N_NATIONKEY  AND CUSTOMER.C_ACCTBAL <= 5 AND NATION.N_NATIONKEY <= 5"
test_query_2 = "/*+ NoSeqScan(nation) */ SELECT PS_PARTKEY, SUM(PS_SUPPLYCOST * PS_AVAILQTY) AS VALUE  FROM PARTSUPP, SUPPLIER, NATION WHERE PS_SUPPKEY = S_SUPPKEY  AND S_NATIONKEY = N_NATIONKEY AND N_NAME = 'SAUDI ARABIA'  GROUP BY PS_PARTKEY HAVING  SUM(PS_SUPPLYCOST * PS_AVAILQTY) > (SELECT SUM(PS_SUPPLYCOST * PS_AVAILQTY) * 0.0001000000  FROM PARTSUPP, SUPPLIER, NATION WHERE PS_SUPPKEY = S_SUPPKEY AND S_NATIONKEY = N_NATIONKEY AND N_NAME = 'SAUDI ARABIA') ORDER BY VALUE DESC LIMIT 1;"

adding_hints_to_original_query(test_query)


def process_whatif_query(sql_query, query_execution_plan):
    modified_query = sql_query
    modified_plan = query_execution_plan
    return modified_query, modified_plan
