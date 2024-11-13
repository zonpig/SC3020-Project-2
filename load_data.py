import psycopg2

# Database connection details
connection = psycopg2.connect(
    host="localhost",
    database="TPC-H",
    user="postgres",
    password="password",
    port="5433",
)

# Define the file paths and table names in the desired order
csv_files = [
    ("data/1region.csv", "region"),
    ("data/1nation.csv", "nation"),
    ("data/1customer.csv", "customer"),
    ("data/1orders.csv", "orders"),
    ("data/1supplier.csv", "supplier"),
    ("data/1part.csv", "part"),
    ("data/1partsupp.csv", "partsupp"),
    ("data/1lineitem.csv", "lineitem"),
]


# Function to load a CSV file into a specified table using COPY
def bulk_import_csv_to_table(cursor, file_path, table_name):
    with open(file_path, mode="r") as file:
        cursor.copy_expert(
            f"COPY public.{table_name} FROM STDIN WITH (FORMAT csv, DELIMITER '|')",
            file,
        )


try:
    cursor = connection.cursor()

    # Import each CSV file into the corresponding table
    for file_path, table_name in csv_files:
        print(f"Bulk importing data from {file_path} into {table_name}...")
        bulk_import_csv_to_table(cursor, file_path, table_name)
        print(f"Data bulk imported into {table_name} successfully.")

    # Commit all changes
    connection.commit()
    print("All data bulk imported successfully.")

except Exception as error:
    print(f"Error importing data: {error}")
    connection.rollback()  # Rollback any changes if an error occurs

finally:
    # Close cursor and connection
    if "cursor" in locals():
        cursor.close()
    if "connection" in locals():
        connection.close()
