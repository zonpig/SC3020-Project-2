from typing import Dict, Tuple, Any
import time
import json
from preprocessing import (
    Database,
    get_plan_summary,
    get_natural_explanation,
)
from psycopg2 import ProgrammingError
from typing import Dict, Tuple, Any


def process_whatif_query(
    user_query: str, relations: Dict, parameters: Dict
) -> Tuple[bool, Dict[str, Any]]:
    """
    Process what-if analysis for query optimization with SQL rewrites based on user parameters.
    """
    try:
        connection = Database.get_connection()

        with connection.cursor() as cur:
            # Apply what-if parameters with proper formatting
            for param, value in parameters.items():
                try:
                    # Handle boolean parameters (enable_*)
                    if param.startswith("enable_"):
                        value_str = "on" if value else "off"
                        cur.execute(f"SET {param} = {value_str};")

                    # Handle memory parameters (need quotes)
                    elif param in [
                        "work_mem",
                        "maintenance_work_mem",
                        "effective_cache_size",
                    ]:
                        cur.execute(f"SET {param} = '{value}';")

                    # Handle numeric parameters
                    elif isinstance(value, (int, float)):
                        cur.execute(f"SET {param} = {value};")

                    # Handle string parameters
                    else:
                        cur.execute(f"SET {param} = '{value}';")

                except Exception as e:
                    print(
                        f"Warning: Failed to set parameter {param} = {value}: {str(e)}"
                    )
                    continue

            try:
                # Get the query plan
                explain_query = f"""
                EXPLAIN (ANALYZE true, COSTS true, TIMING true, BUFFERS true, FORMAT JSON)
                {user_query}
                """
                cur.execute(explain_query)
                plan_data = cur.fetchall()[0][0][0]

                # Extract the plan
                plan = plan_data.get("Plan", {})

                # Save plan
                plan_json_name = f"plan_whatif_{str(time.time())}.json"
                with open(plan_json_name, "w") as f:
                    json.dump(plan, f)

                return False, {
                    "plan_data_path": plan_json_name,
                    "summary_data": get_plan_summary(plan),
                    "natural_explain": get_natural_explanation(plan),
                    "block_analysis": analyze_blocks(plan),
                    "applied_parameters": parameters,
                    "query_transformation": {
                        "original_query": user_query,
                        "rewritten_query": user_query,
                        "transformation_reason": analyze_transformation(
                            plan_data, user_query
                        ),
                        "planner_settings": parameters,
                    },
                }

            except ProgrammingError as e:
                cur.execute("ROLLBACK;")
                return True, {"msg": f"Error during what-if analysis: {str(e)}"}

    except Exception as e:
        return True, {"msg": f"An error has occurred: {repr(e)}"}
    finally:
        if "connection" in locals():
            connection.close()


def clean_and_format_query(query: str) -> str:
    """
    Clean and format the query by removing duplicates and fixing formatting.
    """
    # Split query into components
    parts = query.split("\n")

    # Remove duplicates while preserving order
    seen = set()
    cleaned_parts = []
    for part in parts:
        # Clean up whitespace
        cleaned = " ".join(part.strip().split())
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            cleaned_parts.append(part)

    # Handle specific clauses to prevent duplication
    unique_clauses = {
        "GROUP BY": [],
        "ORDER BY": [],
        "JOIN": [],
    }

    final_parts = []
    current_clause = None

    for part in cleaned_parts:
        stripped = part.strip().upper()

        # Check for clause starts
        for clause in unique_clauses:
            if stripped.startswith(clause):
                current_clause = clause
                break

        if current_clause:
            if stripped not in unique_clauses[current_clause]:
                unique_clauses[current_clause].append(stripped)
        else:
            final_parts.append(part)

    # Add back unique clauses
    for clause, items in unique_clauses.items():
        if items:
            final_parts.extend(items)

    # Return formatted query
    return "\n".join(final_parts)


def format_sql(query: str) -> str:
    """
    Format SQL query with proper indentation and line breaks.
    """
    keywords = [
        "SELECT",
        "FROM",
        "WHERE",
        "GROUP BY",
        "ORDER BY",
        "HAVING",
        "JOIN",
        "WITH",
    ]
    lines = query.split("\n")
    formatted = []
    indent_level = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Adjust indent for keywords
        for keyword in keywords:
            if line.upper().startswith(keyword):
                indent_level = 0 if keyword == "WITH" else 1
                break

        # Add proper indentation
        formatted.append("    " * indent_level + line)

        # Increase indent after certain keywords
        if line.upper().startswith(("WITH", "SELECT")):
            indent_level += 1

    return "\n".join(formatted)


def analyze_blocks(plan: Dict) -> Dict[str, list]:
    """
    Analyze query blocks from the execution plan
    """
    blocks = {
        "scan_blocks": [],
        "join_blocks": [],
        "filter_blocks": [],
        "aggregate_blocks": [],
    }

    def analyze_node(node: Dict):
        if not isinstance(node, dict):
            return

        # Analyze node type
        node_type = node.get("Node Type", "")

        # Categorize scan operations
        if "Scan" in node_type:
            scan_detail = f"{node_type} on {node.get('Relation Name', 'unknown')}"
            if node.get("Index Name"):
                scan_detail += f" using index {node.get('Index Name')}"
            blocks["scan_blocks"].append(scan_detail)

        # Categorize join operations
        elif "Join" in node_type:
            join_detail = f"{node_type}"
            if node.get("Hash Cond"):
                join_detail += f" with condition {node.get('Hash Cond')}"
            elif node.get("Merge Cond"):
                join_detail += f" with condition {node.get('Merge Cond')}"
            blocks["join_blocks"].append(join_detail)

        # Categorize filter operations
        if node.get("Filter"):
            blocks["filter_blocks"].append(f"Filter: {node.get('Filter')}")

        # Categorize aggregate operations
        if "Aggregate" in node_type:
            agg_detail = f"{node_type}"
            if node.get("Group Key"):
                agg_detail += f" by {', '.join(node.get('Group Key'))}"
            blocks["aggregate_blocks"].append(agg_detail)

        # Recursively analyze child nodes
        if "Plans" in node:
            for child_node in node["Plans"]:
                analyze_node(child_node)

    analyze_node(plan)
    return blocks


def analyze_transformation(plan_data: Dict, original_query: str) -> str:
    """
    Analyze why the query was transformed based on the plan.
    """
    reasons = []
    plan = plan_data.get("Plan", {})

    # Analyze node types
    if "Node Type" in plan:
        node_type = plan["Node Type"]
        if node_type == "Hash Join":
            reasons.append("Query uses hash join for better performance")
        elif node_type == "Index Scan":
            reasons.append("Query uses index scan")
        elif node_type == "Merge Join":
            reasons.append("Query uses merge join")

    # Analyze subplans
    if "Plans" in plan:
        for subplan in plan["Plans"]:
            if subplan.get("Node Type") == "Index Scan":
                reasons.append("Query uses indexes for faster data access")
            elif subplan.get("Node Type") == "Hash":
                reasons.append("Query uses hash tables for efficient joining")

    # Check for predicate pushdown
    if "Filter" in plan:
        reasons.append("Query pushes down predicates for earlier filtering")

    return (
        " and ".join(reasons)
        if reasons
        else "Query optimized based on planner settings"
    )


error, results = process_whatif_query(
    user_query="""
    /*+ Leading(l o c) HashJoin(o) HashJoin(c) */
    SELECT 
        l.l_orderkey,
        SUM(l.l_extendedprice * (1 - l.l_discount)) AS revenue,
        o.o_orderdate,
        o.o_shippriority
    FROM 
        (SELECT l_orderkey, l_extendedprice, l_discount
         FROM lineitem 
         WHERE l_extendedprice > 10) l
    JOIN 
        (SELECT o_orderkey, o_custkey, o_orderdate, o_shippriority
         FROM orders 
         WHERE o_totalprice > 10) o 
    ON l.l_orderkey = o.o_orderkey
    JOIN 
        (SELECT /*+ IndexScan(customer) */ c_custkey 
         FROM customer 
         WHERE c_mktsegment = 'BUILDING') c 
    ON o.o_custkey = c.c_custkey
    GROUP BY 
        l.l_orderkey,
        o.o_orderdate,
        o.o_shippriority
    ORDER BY 
        revenue DESC,
        o_orderdate;
    """,
    relations="TPC-H",
    parameters={
        # Scan method controls
        "enable_seqscan": False,
        "enable_indexscan": True,
        "enable_indexonlyscan": True,
        "enable_bitmapscan": False,
        # Join method controls
        "enable_hashjoin": False,
        "enable_mergejoin": False,
        "enable_nestloop": True,
        # Cost parameters
        "random_page_cost": 1.1,
        "cpu_tuple_cost": 0.01,
        "cpu_index_tuple_cost": 0.001,
        # Memory parameters
        "work_mem": "1GB",
        "effective_cache_size": "4GB",
        # Aggressive optimization parameters
        "enable_material": True,
        "join_collapse_limit": 1,
        "from_collapse_limit": 1,
        "geqo_threshold": 12,
        "constraint_exclusion": "partition",
        # Additional optimizations
        "enable_parallel_append": True,
        "enable_parallel_hash": True,
        "max_parallel_workers_per_gather": 4,
        "parallel_setup_cost": 1000,
        "parallel_tuple_cost": 0.1,
        # Force materialization
        "enable_material": True,
        "min_parallel_table_scan_size": "8MB",
        "min_parallel_index_scan_size": "512kB",
    },
)

if not error:
    summary_data = results["summary_data"]

    # Print all summary metrics
    print("Plan Summary:")
    print(f"Total Cost: {summary_data['total_cost']}")

    # Block statistics
    print("\nBlock Statistics:")
    print(f"Hit Blocks: {summary_data['total_blocks']['hit_blocks']}")
    print(f"Read Blocks: {summary_data['total_blocks']['read_blocks']}")

    # Node count
    print(f"\nTotal Nodes in Plan: {summary_data['nodes_count']}")

    # Natural explanation
    print("\nNatural Explanation:")
    for step in results["natural_explain"]:
        print(f"- {step}")

    # Block analysis
    print("\nBlock Analysis:")
    print("Scan Operations:")
    for scan in results["block_analysis"]["scan_blocks"]:
        print(f"- {scan}")

    print("\nJoin Operations:")
    for join in results["block_analysis"]["join_blocks"]:
        print(f"- {join}")

    print("\nFilter Operations:")
    for filter_op in results["block_analysis"]["filter_blocks"]:
        print(f"- {filter_op}")

    print("\nAggregate Operations:")
    for agg in results["block_analysis"]["aggregate_blocks"]:
        print(f"- {agg}")

    # Query transformation details
    print("\nQuery Transformation:")
    print(f"Original Query: {results['query_transformation']['original_query']}")
    print(f"Rewritten Query: {results['query_transformation']['rewritten_query']}")
    print(
        f"Transformation Reason: {results['query_transformation']['transformation_reason']}"
    )

    # Applied parameters
    print("\nApplied Parameters:")
    for param, value in results["applied_parameters"].items():
        print(f"{param}: {value}")
else:
    print(f"Error occurred: {results['msg']}")
