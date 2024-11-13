# SC3020-Project-2

## Goal

The goal of the project can be described with an example. Consider the SQL query in Figure 1. The simplified view of the QEP for execution of this query in PostgreSQL is given on the right. Observe that as a user I may want to know what will be the impact on the cost if I change the hash join to merge join? Or what will be the cost when I replace the sequential scan with an index scan on one of the tables? The project aims to build a software to enable such what-if questions on QEPs. To this end, the project should address the following problems:

• Enable manipulation and editing of the visual tree view of the QEP to specify these what-if questions.  
• Generate the corresponding SQL query based on the what-if question by exploiting the planner method configuration of PostgreSQL.  
• Retrieve the AQP associated with the modified SQL and compare its cost with the original QEP.

## Addressing the problem statement

(a) Design and implement an efficient algorithm that takes as input the original SQL query, the modified visual QEP with what-if questions, and returns as output a modified SQL query and its corresponding QEP (which is the AQP) that describes the execution of various components of the query based on the what-if questions. Additionally, the cost of the AQP needs to be compared with that of the original QEP to shed insights into the impact of the changes of the physical operators/join order on the estimated cost. Your goal is to ensure generality of the solution (i.e., it can handle a wide variety of queries and should be independent of the underlying database schema).

Hence, your software should work on any database schema and for a wide variety of SQL queries on it. In other words, you should not be hardcoding SQL queries or schema-specific information.

(b) Design and implement a user-friendly graphical user interface (GUI) to support your what-if analysis software. You can imagine that through it you can choose the database schema (TPC-H in this case), specify the SQL query in the Query panel, visualize the QEP on the QEP panel which you can interactively edit for posing what-if questions. Your GUI should also have a panel to visualize the modified SQL generated based on the what-if question, and another panel to view the corresponding AQP along with cost comparison with the original QEP

## Submission Requirements

You should submit four program files: interface.py, whatif.py, preprocessing.py, and project.py.
The file interface.py contains the code for the GUI (you may use any other GUI development toolkit as long as it is compatible with Python).

The preprocessing.py file contains any code for reading inputs and any preprocessing necessary to make your algorithm work.

The whatif.py contains code for generating the modified SQL and corresponding AQP.

Lastly, the project.py is the main file that invokes all the necessary procedures from these three files.

Note that we shall be running the project.py file (either from command prompt or using the Pycharm IDE) to execute the software.

Make sure your code follows good coding practice: sufficient comments, proper variable/function naming,
etc. We will execute the software to check its correctness using different query sets and dataset to check for the generality of the solution. We will also check quality of algorithm design w.r.t processing of the query plans and what-if questions.

## Flow

Project.py -> Interface.py

If have TPC-H database, can load default sql queries from the database

Else, can input custom sql queries

## Creating TPC-H database in PostgreSQL

Download TPC-H_Tools_v3.0.1.zip

Docker Environment
To set it up, run the following commands:

```bash
docker compose create
docker compose start
```

After starting the docker environment, connect the server to pgadmin and create a new database called **TPC-H**.

To create the tables in postgresql, run the following commands:

```bash
python create_tables.py
```

Use the below command to check if pg_load_hints is loaded:

```bash
SHOW shared_preload_libraries;
```

Order of importing the data

1. region
2. nation
3. customer
4. orders
5. supplier
6. part
7. partsupp
8. lineitem

## Running the project

In preprocessing.py, take note of the below code block:

```python
class Database:
    connection = None

    @classmethod
    def get_connection(cls):
        if cls.connection is None:
            cls.connection = psycopg2.connect(
                host="localhost",
                database="TPC-H",
                user="postgres", # Change this to your username
                password="password", # Change this to your password
                port="5433",
            )
        return cls.connection
```

## Note

To install pygraphviz on mac, run the following commands:

```bash
brew install graphviz
pip3 install \
    --config-setting="--global-option=build_ext" \
    --config-setting="--global-option=-I$(brew --prefix graphviz)/include/" \
    --config-setting="--global-option=-L$(brew --prefix graphviz)/lib/" \
    --use-pep517 \
    pygraphviz
```



To install pygraphviz on windows, do the following steps:

1. Go to the website `https://www.graphviz.org/download/` and download the 64-bit EXE installer for Windows.
2. Add Graphviz to PATH
    1) Open System Properties: Press `Win + R`, type `sysdm.cpl`, and press **Enter**.
    2) Go to the **Advanced** tab and click on **Environment Variables**.
    3) Under **System Variables**, find the **Path variable** and click **Edit**.
    4) Click **New** and add the following paths:
       - `C:\Program Files\Graphviz\bin`
       - `C:\Program Files\Graphviz\include`
       - `C:\Program Files\Graphviz\lib`
    6) Click **OK** to save the changes and close the windows.
3. Run the following command in a new command prompt
   
```bash
pip install pygraphviz --global-option=build_ext --global-option="-I<C:\Program Files\Graphviz\include>" --global-option="-L<C:\Program Files\Graphviz\lib>"
```

4. You can verify your installation by running the following code in Python:

```bash
import pygraphviz as pgv
print(pgv.__version__)
```

Testing Command for whatif

```bash
pytest --cov=whatif --cov-report=term --cov-report=xml:coverage.xml
```

References:
pg_hint_plan: <https://github.com/ossc-db/pg_hint_plan>
