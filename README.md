# SC3020-Project-2

## Goal

The goal of the project can be described with an example. Consider the SQL query in
Figure 1. The simplified view of the QEP for execution of this query in PostgreSQL is given on the right. Observe that as a user I may want to know what will be the impact on the cost if I change the hash join to merge join? Or what will be the cost when I replace the sequential scan with an index scan on one of the tables? The project aims to build a software to enable such what-if questions on QEPs. To this end, the project should address the following problems:

• Enable manipulation and editing of the visual tree view of the QEP to specify these what-if questions.  
• Generate the corresponding SQL query based on the what-if question by exploiting the planner method configuration of PostgreSQL.  
• Retrieve the AQP associated with the modified SQL and compare its cost with the original QEP.

## Addressing the problem statement

(a) Design and implement an efficient algorithm that takes as input the original SQL
query, the modified visual QEP with what-if questions, and returns as output a
modified SQL query and its corresponding QEP (which is the AQP) that describes
the execution of various components of the query based on the what-if
questions. Additionally, the cost of the AQP needs to be compared with that of
the original QEP to shed insights into the impact of the changes of the physical  
operators/join order on the estimated cost. Your goal is to ensure generality of the solution (i.e., it can handle a wide variety of queries and should be independent of the underlying database schema).

Hence, your software should work on any database schema and for a wide variety of SQL queries on it. In other words, you should not be hardcoding SQL queries or schema-specific information.

(b) Design and implement a user-friendly graphical user interface (GUI) to support your what-if analysis software. You can imagine that through it you can choose the database schema (TPC-H in this case), specify the SQL query in the Query panel, visualize the QEP on the QEP panel which you can interactively edit for posing what-if questions. Your GUI should also have a panel to visualize the modified SQL generated based on the what-if question, and another panel to view the corresponding AQP along with cost comparison with the original QEP

## Creating TPC-H database in PostgreSQL

Download TPC-H_Tools_v3.0.1.zip

To create the tables in postgresql, can refer to [create_tables](create_tables.md)

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
                port="5432",
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
