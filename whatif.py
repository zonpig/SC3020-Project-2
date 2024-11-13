import time
import json
from preprocessing import (
    Database,
    get_plan_summary,
    get_natural_explanation,
    get_block_analysis,
)
from psycopg2 import ProgrammingError, OperationalError


def process_whatif_query(user_query, relations, parameters):
    """
    Process what-if analysis for query optimization based on user parameters.

    Args:
        user_query: SQL query to analyze
        relations: Database relation information
        parameters: Dict containing what-if parameters:
            {
                "enable_seqscan": bool,
                "enable_indexscan": bool,
                "enable_indexonlyscan": bool,
                "enable_bitmapscan": bool,
                "enable_hashjoin": bool,
                "enable_mergejoin": bool,
                "enable_nestloop": bool,
                "random_page_cost": float,
                "cpu_tuple_cost": float,
                "cpu_index_tuple_cost": float,
                "cpu_operator_cost": float,
                "effective_cache_size": str,
                "work_mem": str
            }

    Returns:
        tuple: (error_occurred, result_dict)
    """
    query_str = f"EXPLAIN (ANALYZE, COSTS, SETTINGS, VERBOSE, BUFFERS, SUMMARY, FORMAT JSON) {user_query};"

    try:
        connection = Database.get_connection()

        with connection.cursor() as cur:
            # Apply what-if parameters
            for param in [
                "seqscan",
                "indexscan",
                "indexonlyscan",
                "bitmapscan",
                "hashjoin",
                "mergejoin",
                "nestloop",
            ]:
                value = "on" if parameters.get(f"enable_{param}", True) else "off"
                cur.execute(f"SET enable_{param} = {value};")

            # Cost parameters
            if parameters.get("random_page_cost"):
                cur.execute(
                    f"SET random_page_cost = {float(parameters['random_page_cost'])};"
                )
            if parameters.get("cpu_tuple_cost"):
                cur.execute(
                    f"SET cpu_tuple_cost = {float(parameters['cpu_tuple_cost'])};"
                )
            if parameters.get("cpu_index_tuple_cost"):
                cur.execute(
                    f"SET cpu_index_tuple_cost = {float(parameters['cpu_index_tuple_cost'])};"
                )
            if parameters.get("cpu_operator_cost"):
                cur.execute(
                    f"SET cpu_operator_cost = {float(parameters['cpu_operator_cost'])};"
                )

            # Memory parameters
            if parameters.get("effective_cache_size"):
                cur.execute(
                    f"SET effective_cache_size = '{parameters['effective_cache_size']}';"
                )
            if parameters.get("work_mem"):
                cur.execute(f"SET work_mem = '{parameters['work_mem']}';")

            try:
                # Get what-if plan
                cur.execute(query_str)
                plan = cur.fetchall()[0][0][0].get("Plan")

                # Save plan
                plan_json_name = f"plan_whatif_{str(time.time())}.json"
                with open(plan_json_name, "w") as f:
                    json.dump(plan, f)

                return False, {
                    "plan_data_path": plan_json_name,
                    "summary_data": get_plan_summary(plan),
                    "natural_explain": get_natural_explanation(plan),
                    "block_analysis": get_block_analysis(
                        user_query, relations, connection
                    ),
                    "applied_parameters": parameters,
                }

            except ProgrammingError as e:
                cur.execute("ROLLBACK;")
                return True, {"msg": f"Error during what-if analysis: {str(e)}"}

    except OperationalError:
        return True, {
            "msg": "Failed to connect to the database! Please ensure that the database is running."
        }
    except Exception as e:
        return True, {"msg": f"An error has occurred: {repr(e)}"}
