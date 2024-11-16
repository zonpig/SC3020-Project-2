-- Create the TPC-H database
CREATE DATABASE "TPC-H";

-- Load the pg_hint_plan extension in the TPC-H database
\connect "TPC-H"

CREATE EXTENSION IF NOT EXISTS pg_hint_plan;

-- Create the region table
CREATE TABLE public.region (
    r_regionkey integer NOT NULL,
    r_name character(25) COLLATE pg_catalog."default" NOT NULL,
    r_comment character varying(152) COLLATE pg_catalog."default",
    CONSTRAINT region_pkey PRIMARY KEY (r_regionkey)
) WITH (OIDS = FALSE) TABLESPACE pg_default;
ALTER TABLE public.region OWNER to postgres;

-- Create the nation table
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

-- Create the part table
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

-- Continue creating the other tables similarly
-- (Rest of your table creation code goes here)
