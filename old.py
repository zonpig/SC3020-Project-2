import json
import re

from flask import Flask, jsonify, render_template, request, url_for

from interface import visualize_query_plan
from preprocessing import (
    get_relation_block,
    process_query,
    get_postgres_schemas,
    Database,
)

app = Flask(__name__)


@app.route("/")
@app.route("/index.html")
def dashboard():
    return render_template("index.html")


@app.route("/api/getSampleQueries", methods=["GET"])
def api_getData():
    queries = [
        "SELECT customer.c_name, nation.n_name FROM customer, nation WHERE customer.c_nationkey = nation.n_nationkey and customer.c_acctbal <= 5 and nation.n_nationkey <= 5",
        "select sum(l_extendedprice * l_discount) as revenue from lineitem where l_shipdate >= date '1995-01-01' and l_shipdate < date '1995-01-01' + interval '1' year and l_discount between 0.09 - 0.01 and 0.09 + 0.01 and l_quantity < 24;",
        "select ps_partkey, sum(ps_supplycost * ps_availqty) as value from partsupp, supplier, nation where ps_suppkey = s_suppkey and s_nationkey = n_nationkey and n_name = 'SAUDI ARABIA' group by ps_partkey having sum(ps_supplycost * ps_availqty) > (select sum(ps_supplycost * ps_availqty) * 0.0001000000 from partsupp, supplier, nation where ps_suppkey = s_suppkey and s_nationkey = n_nationkey and n_name = 'SAUDI ARABIA') order by value desc limit 1;",
    ]
    return jsonify(queries)


@app.route("/api/runQuery", methods=["POST"])
def run_query():
    print("run_query")
    data = request.json
    print(data)
    query = data.get("query")
    query = re.sub(r"\s+", " ", query)
    relations = data.get("relations")

    result = {"query": query}

    has_error, response = process_query(query, relations)
    if has_error:
        result["error"] = response["msg"]
    else:
        json_path = response["plan_data_path"]
        with open(json_path, "r") as json_file:
            plan = json.load(json_file)
        url = visualize_query_plan(plan)  # Generate the image
        # Assuming the image is saved in a static directory
        image_url = url_for("static", filename=url)

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
    # print(result)
    return jsonify(result)


@app.route("/api/runAlternateQuery", methods=["POST"])
def run_alternate_query():
    print("run_whatif")
    data = request.json
    print(data)
    query = data.get("query")
    query = re.sub(r"\s+", " ", query)
    relations = data.get("relations")

    result = {"query": query}

    has_error, response = process_query(query, relations)
    if has_error:
        result["error"] = response["msg"]
    else:
        json_path = response["plan_data_path"]
        with open(json_path, "r") as json_file:
            plan = json.load(json_file)
        url = visualize_query_plan(plan)  # Generate the image
        # Assuming the image is saved in a static directory
        image_url = url_for("static", filename=url)

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
    # print(result)
    return jsonify(result)


@app.route("/api/explore-block", methods=["POST"])
def explore_block():
    # Obtain specific fields from POST request
    data = request.json
    relation = data.get("relation")
    block_id = data.get("blockName")
    result = {}

    # Call function which queries database based on query that fulfills the relation & block_id obtained above
    has_error, response, column_name = get_relation_block(relation, block_id)
    print(column_name)
    if has_error:  # If error with querying, notify
        result["error"] = "Query process error."
    else:  # Else, obtain data records, block number, sequence number and column_names
        result["data"] = response["block_info"]
        result["column_name"] = column_name
    return jsonify(result)


@app.route("/api/generate-query-plan", methods=["POST"])
def generate_query_plan():
    plan = request.json["plan"]
    url = visualize_query_plan(plan)  # Generate the image

    # Assuming the image is saved in a static directory
    image_url = url_for("static", filename=url)
    return jsonify({"imageUrl": image_url})


@app.route("/api/generate-alternative-query-plan", methods=["POST"])
def process_whatif_query():
    plan = request.json["plan"]
    url = visualize_query_plan(plan)  # Generate the image

    # Assuming the image is saved in a static directory
    image_url = url_for("static", filename=url)
    return jsonify({"imageUrl": image_url})


@app.route("/api/get_schemas")
def get_schemas():
    schemas = get_postgres_schemas()
    return jsonify(schemas)


@app.route("/api/set_database", methods=["GET"])
def set_database():
    try:
        new_database = request.args.get("database")
        if new_database:
            # Update the database in the Database class
            Database.set_database(new_database)
            return jsonify(
                {"message": f"Database updated to {new_database} successfully."}
            )
        else:
            return jsonify({"error": "No database provided"}), 400
    except Exception as e:
        print(f"Error updating database: {e}")
        return jsonify({"error": "Failed to update database"}), 500


if __name__ == "__main__":
    # os.add_dll_directory("C://Users/SC3020/Anaconda3/DLLs")
    app.run(debug=True)
