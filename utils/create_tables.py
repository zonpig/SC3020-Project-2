import psycopg

# Define the SQL statements for creating tables
table_creation_queries = [
    """
    CREATE TABLE public.region (
        r_regionkey integer NOT NULL,
        r_name character(25) COLLATE pg_catalog."default" NOT NULL,
        r_comment character varying(152) COLLATE pg_catalog."default",
        CONSTRAINT region_pkey PRIMARY KEY (r_regionkey)
    ) WITH (OIDS = FALSE) TABLESPACE pg_default;
    ALTER TABLE public.region OWNER to postgres;
    """,
    """
    CREATE TABLE public.nation (
        n_nationkey integer NOT NULL,
        n_name character(25) COLLATE pg_catalog."default" NOT NULL,
        n_regionkey integer NOT NULL,
        n_comment character varying(152) COLLATE pg_catalog."default",
        CONSTRAINT nation_pkey PRIMARY KEY (n_nationkey),
        CONSTRAINT fk_nation FOREIGN KEY (n_regionkey)
            REFERENCES public.region (r_regionkey) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
    ) WITH (OIDS = FALSE) TABLESPACE pg_default;
    ALTER TABLE public.nation OWNER to postgres;
    """,
    """
    CREATE TABLE public.part (
        p_partkey integer NOT NULL,
        p_name character varying(55) COLLATE pg_catalog."default" NOT NULL,
        p_mfgr character(25) COLLATE pg_catalog."default" NOT NULL,
        p_brand character(10) COLLATE pg_catalog."default" NOT NULL,
        p_type character varying(25) COLLATE pg_catalog."default" NOT NULL,
        p_size integer NOT NULL,
        p_container character(10) COLLATE pg_catalog."default" NOT NULL,
        p_retailprice numeric(15,2) NOT NULL,
        p_comment character varying(23) COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT part_pkey PRIMARY KEY (p_partkey)
    ) WITH (OIDS = FALSE) TABLESPACE pg_default;
    ALTER TABLE public.part OWNER to postgres;
    """,
    """
    CREATE TABLE public.supplier (
        s_suppkey integer NOT NULL,
        s_name character(25) COLLATE pg_catalog."default" NOT NULL,
        s_address character varying(40) COLLATE pg_catalog."default" NOT NULL,
        s_nationkey integer NOT NULL,
        s_phone character(15) COLLATE pg_catalog."default" NOT NULL,
        s_acctbal numeric(15,2) NOT NULL,
        s_comment character varying(101) COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT supplier_pkey PRIMARY KEY (s_suppkey),
        CONSTRAINT fk_supplier FOREIGN KEY (s_nationkey)
            REFERENCES public.nation (n_nationkey) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
    ) WITH (OIDS = FALSE) TABLESPACE pg_default;
    ALTER TABLE public.supplier OWNER to postgres;
    """,
    """
    CREATE TABLE public.partsupp (
        ps_partkey integer NOT NULL,
        ps_suppkey integer NOT NULL,
        ps_availqty integer NOT NULL,
        ps_supplycost numeric(15,2) NOT NULL,
        ps_comment character varying(199) COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT partsupp_pkey PRIMARY KEY (ps_partkey, ps_suppkey),
        CONSTRAINT fk_ps_suppkey_partkey FOREIGN KEY (ps_partkey)
            REFERENCES public.part (p_partkey) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION,
        CONSTRAINT fk_ps_suppkey_suppkey FOREIGN KEY (ps_suppkey)
            REFERENCES public.supplier (s_suppkey) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
    ) WITH (OIDS = FALSE) TABLESPACE pg_default;
    ALTER TABLE public.partsupp OWNER to postgres;
    """,
    """
    CREATE TABLE public.customer (
        c_custkey integer NOT NULL,
        c_name character varying(25) COLLATE pg_catalog."default" NOT NULL,
        c_address character varying(40) COLLATE pg_catalog."default" NOT NULL,
        c_nationkey integer NOT NULL,
        c_phone character(15) COLLATE pg_catalog."default" NOT NULL,
        c_acctbal numeric(15,2) NOT NULL,
        c_mktsegment character(10) COLLATE pg_catalog."default" NOT NULL,
        c_comment character varying(117) COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT customer_pkey PRIMARY KEY (c_custkey),
        CONSTRAINT fk_customer FOREIGN KEY (c_nationkey)
            REFERENCES public.nation (n_nationkey) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
    ) WITH (OIDS = FALSE) TABLESPACE pg_default;
    ALTER TABLE public.customer OWNER to postgres;
    """,
    """
    CREATE TABLE public.orders (
        o_orderkey integer NOT NULL,
        o_custkey integer NOT NULL,
        o_orderstatus character(1) COLLATE pg_catalog."default" NOT NULL,
        o_totalprice numeric(15,2) NOT NULL,
        o_orderdate date NOT NULL,
        o_orderpriority character(15) COLLATE pg_catalog."default" NOT NULL,
        o_clerk character(15) COLLATE pg_catalog."default" NOT NULL,
        o_shippriority integer NOT NULL,
        o_comment character varying(79) COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT orders_pkey PRIMARY KEY (o_orderkey),
        CONSTRAINT fk_orders FOREIGN KEY (o_custkey)
            REFERENCES public.customer (c_custkey) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
    ) WITH (OIDS = FALSE) TABLESPACE pg_default;
    ALTER TABLE public.orders OWNER to postgres;
    """,
    """
    CREATE TABLE public.lineitem (
        l_orderkey integer NOT NULL,
        l_partkey integer NOT NULL,
        l_suppkey integer NOT NULL,
        l_linenumber integer NOT NULL,
        l_quantity numeric(15,2) NOT NULL,
        l_extendedprice numeric(15,2) NOT NULL,
        l_discount numeric(15,2) NOT NULL,
        l_tax numeric(15,2) NOT NULL,
        l_returnflag character(1) COLLATE pg_catalog."default" NOT NULL,
        l_linestatus character(1) COLLATE pg_catalog."default" NOT NULL,
        l_shipdate date NOT NULL,
        l_commitdate date NOT NULL,
        l_receiptdate date NOT NULL,
        l_shipinstruct character(25) COLLATE pg_catalog."default" NOT NULL,
        l_shipmode character(10) COLLATE pg_catalog."default" NOT NULL,
        l_comment character varying(44) COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT lineitem_pkey PRIMARY KEY (l_orderkey, l_partkey, l_suppkey, l_linenumber),
        CONSTRAINT fk_lineitem_orderkey FOREIGN KEY (l_orderkey)
            REFERENCES public.orders (o_orderkey) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION,
        CONSTRAINT fk_lineitem_partkey FOREIGN KEY (l_partkey)
            REFERENCES public.part (p_partkey) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION,
        CONSTRAINT fk_lineitem_suppkey FOREIGN KEY (l_suppkey)
            REFERENCES public.supplier (s_suppkey) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
    ) WITH (OIDS = FALSE) TABLESPACE pg_default;
    ALTER TABLE public.lineitem OWNER to postgres;
    """,
]

# Connect to the database and execute the queries
try:
    # Establish the connection
    connection = psycopg.connect(
        host="localhost",
        dbname="TPC-H",
        user="postgres",
        password="password",
        port="5433",
    )
    cursor = connection.cursor()

    # Load pg_hint_plan extension
    cursor.execute("LOAD 'pg_hint_plan';")
    print("pg_hint_plan loaded successfully.")

    # Execute each table creation query
    for query in table_creation_queries:
        cursor.execute(query)
        print("Table created successfully.")

    # Commit changes
    connection.commit()
    print("All tables created successfully.")

except Exception as error:
    print(f"Error creating tables: {error}")

finally:
    # Close cursor and connection if they exist
    if "cursor" in locals():
        cursor.close()
    if "connection" in locals():
        connection.close()
