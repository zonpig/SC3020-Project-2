# Code for reading inputs and any preprocessing to make your algorithm work


from collections import deque
import logging
import json
import time
import psycopg2
from psycopg2 import ProgrammingError, OperationalError

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
                port="5432",
            )
        return cls.connection


####
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


####################################### Core Function #######################################
"""
Main Function : get_relation_block

>> Get relation's block information by relation_name and block_id

>> Returns:
    - error boolean: True if error, False otherwise
    - result dictionary: contains message if error, else contains block_information
"""


def get_relation_block(relation, block_id):
    print("here")
    print(relation)
    query_blockId = (
        f"SELECT ctid, * FROM {relation} WHERE (ctid::text::point)[0] = {block_id};"
    )
    query_columnName = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{relation}' ORDER BY ORDINAL_POSITION"

    connection = Database.get_connection()
    with connection.cursor() as cur:
        try:
            cur.execute(query_blockId)
            res = cur.fetchall()
            cur.execute(query_columnName)
            cols = cur.fetchall()
            print(cols)
            return False, {"block_info": res}, cols
        except ProgrammingError as e:
            print(e)
            cur.execute("ROLLBACK;")
            return True, {"msg": f"Invalid SQL query!"}, None


"""
Main Function : process_query

>> Process query plan for the given user query.

>> Returns:
    - error boolean: True if error, False otherwise
    - result dictionary: contains message if error, else contains plan_data, summary_data and natural_explain
"""


def process_query(user_query, relations):
    query_str = f"EXPLAIN (ANALYZE, COSTS, SETTINGS, VERBOSE, BUFFERS, SUMMARY, FORMAT JSON) {user_query};"

    result = {
        "plan_data_path": None,
        "summary_data": None,
        "natural_explain": None,
        "block_analysis": None,
    }

    try:
        connection = Database.get_connection()

        # get base query plan
        with connection.cursor() as cur:
            try:
                # execute query and get results
                cur.execute(query_str)
                plan = cur.fetchall()[0][0][0].get("Plan")
            except ProgrammingError as e:
                print(e)
                cur.execute("ROLLBACK;")
                return True, {"msg": f"Invalid SQL query!"}

        print("fetched the QEP!")

        # logging
        logging.basicConfig(
            filename="app.log",
            filemode="w",
            format="%(name)s - %(levelname)s - %(message)s",
        )
        logging.warning("This will get logged to a file")
        logging.warning(f"Plan : {plan}")

        # save plan
        plan_json_name = "plan" + str(time.time()) + ".json"
        with open(plan_json_name, "w") as f:
            json.dump(plan, f)

        result["plan_data_path"] = plan_json_name
        # parse results for summary for plan
        result["summary_data"] = get_plan_summary(plan)
        # get natural explanation for plan
        result["natural_explain"] = get_natural_explanation(plan)
        # get block analysis for query
        result["block_analysis"] = get_block_analysis(user_query, relations, connection)

    except OperationalError as e:
        return True, {
            "msg": f"An error has occurred: Failed to connect to the database! Please ensure that the database is running."
        }
    except Exception as e:
        return True, {"msg": f"An error has occurred: {repr(e)}"}

    return False, result


####################################### Annotation Functions #######################################

"""
Function : get_block_analysis

>> Produces a summary given a query query and relations.
    - SQL query response containing the ctids
    - blocks analysis by relation
"""


def get_block_analysis(user_query, relations, connection):
    print("Start Block Analysis ...")
    analysis = {
        "sql_response": None,
        "blocks_by_relation": [],
        "have_ctids": False,
        "is_aggregation": False,
    }

    a_relations = list(relations.keys())

    if user_query.upper().count("FROM (") >= 1:
        print("Detect nested SELECT cases.")
        with connection.cursor() as cur:
            try:
                cur.execute(user_query)
                result = cur.fetchall()
            except ProgrammingError as e:
                print(e)
                cur.execute("ROLLBACK;")
                return None
        print(">>> " + user_query)
        print(result)
        analysis["sql_response"] = {"col": None, "record": None, "result": result}
        analysis["have_ctids"] = False
        return analysis

    ctids = ""
    for relation in a_relations:
        ctids = ctids + f"{relation}.ctid, "

    if is_group_query(user_query):
        from_pos = user_query.upper().find("FROM") - 1
        ctid_user_query = "SELECT " + ctids[:-2]
        if "GROUP BY" in user_query.upper():
            group_pos = user_query.upper().find("GROUP BY") - 1
            ctid_user_query = ctid_user_query + user_query[from_pos:group_pos]
        else:
            ctid_user_query = ctid_user_query + user_query[from_pos:]
        analysis["is_aggregation"] = True
        columns = user_query[7:from_pos].split(", ")
    else:
        ctid_user_query = "SELECT " + ctids + user_query[7:]
        columns = [f"ctid_of_{relation}" for relation in a_relations] + ["record_data"]

    # print(ctid_user_query)

    with connection.cursor() as cur:
        try:
            cur.execute(ctid_user_query)
            ctid_result = cur.fetchall()
            cur.execute(user_query)
            result = cur.fetchall()
        except ProgrammingError as e:
            print(e)
            cur.execute("ROLLBACK;")
            return None

    analysis["sql_response"] = {"col": columns, "record": ctid_result, "result": result}
    analysis["have_ctids"] = True

    blocks = {}
    for relation in a_relations:
        blocks[relation] = set()

    for item in ctid_result:
        for id, relation in enumerate(a_relations):
            if item[id]:
                blocks[relation].add(int(item[id][1:].split(",")[0]))

    for relation in a_relations:
        analysis["blocks_by_relation"].append(
            {
                "relation_name": relation,
                "used_blocks": {
                    "number": len(blocks[relation]),
                    "indexes": sorted(blocks[relation]),
                },
                "total_blocks": get_total_blocks(relations[relation], connection),
            }
        )

    print("Finished Block Analysis!")
    return analysis


def is_group_query(user_query):
    group_funcs = [
        "SUM",
        "MAX",
        "MIN",
        "AVG",
        "COUNT",
    ]  # additional function for aggregate
    for group_func in group_funcs:
        if group_func in user_query.upper():
            return True
    return False


def get_total_blocks(relation, connection):
    with connection.cursor() as cur:
        try:
            cur.execute(f"SELECT MAX(ctid) FROM {relation};")
            query_res = cur.fetchall()
        except ProgrammingError as e:
            print(e)
            cur.execute("ROLLBACK;")
            return None
    return int(query_res[0][0][1:].split(",")[0]) + 1


"""
Function : get_plan_summary

>> Produces a summary given a query plan.
    - Total cost of all nodes
    - Total blocks of all nodes
    - Total number of nodes
"""


def get_plan_summary(plan):
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


"""
Function : get_natural_explain

>> Get the natural explanation given a query plan.
"""


def get_natural_explanation(plan):
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


if __name__ == "__main__":
    test_query = "SELECT SUM(ps_supplycost * ps_availqty) AS value FROM partsupp, supplier, nation WHERE ps_suppkey = s_suppkey AND s_nationkey = n_nationkey AND n_name = 'GERMANY'"
    has_error, result = process_query(test_query, ["partsupp", "supplier", "nation"])
    # has_error, result = process_query("SELECT customer.c_name, nation.n_name FROM customer, nation WHERE customer.c_nationkey = nation.n_nationkey and customer.c_acctbal <= 5 and nation.n_nationkey <= 5", ['customer', 'nation'])
    # has_error, result = get_relation_block("customer", 0)
    if has_error:
        print(result["msg"])
    else:
        print(result)
