# install pg_hint_plan from rpm
FROM docker.io/postgres:17
ADD https://github.com/ossc-db/pg_hint_plan/releases/download/REL17_1_7_0/pg_hint_plan17-1.7.0-1.pg17.rhel8.x86_64.rpm .
RUN  apt-get update -y ; apt-get install -y alien wget ; alien ./pg_hint_plan*.rpm ; dpkg -i pg-hint-plan*.deb

# copy the minimal files to a postgres image
FROM docker.io/postgres:17
COPY --from=0 /usr/pgsql-17/share/extension/pg_hint_plan.control /usr/share/postgresql/17/extension/
COPY --from=0 /usr/pgsql-17/share/extension/pg_hint_plan--1.6.1--1.7.0.sql /usr/share/postgresql/17/extension/

COPY --from=0 /usr/pgsql-17/lib/pg_hint_plan.so /usr/pgsql-17/lib/pg_hint_plan.so /usr/lib/postgresql/17/lib/
ENV  POSTGRES_USER=postgres
ENV  POSTGRES_PASSWORD=password
CMD ["postgres", "-c", "port=5433", "-c", "shared_preload_libraries=pg_hint_plan,pg_stat_statements"]
