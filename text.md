# OOPS projections and automatic table substitution

**OOPS** provides some functions simplifying creation and usage of projections. In future it may be added to SQL grammar, so that it is possible to write:

```sql
CREATE PROJECTION xxx OF TABLE yyy(column1, column2,...) GROUP BY (column1, column2, ...)
```

But right now it can be done using function:

```postgres
create_projection(projection_name text, source_table regclass, vector_columns text[], scalar_columns text[] default null, order_by text default null)
```

First argument of this function specifies name of the projection, second refers to existed **Postgres** table, `vector_columns` is array of column names which should be stores as **OOPS** tiles, `scalar_columns` is array of grouping columns which type is preserved and optional `order_by parameter` specifies name of ordering attribute (explained below). 

The `create_projection(PNAME,...)` functions does the following:
1. Creates projection table with specified name and attributes.
2. Creates `PNAME_refresh()` functions which can be used to update projection.
3. Inserts information about created projection in `OOPS_projections` table. 

This table is used by optimizer to automatically substitute table with projection.

The `order_by` attribute is one of the OOPS projection vector columns by which data is sorted. 
Presence of such column in projection allows to incrementally update projection. 
Generated `PNAME_refresh()` method calls `populate()` method, selecting from original table only rows with `order_by` column value greater than maximal value of this column in projection. 
It assumes that `order_by` is unique or at least refresh is done at the moment when there is some gap in collected events.

Like materialized views, **OOPS** projections are not updated automatically.
It is responsibility of programmer to periodically refresh them. 
The most convenient way is to use generated `PNAME_refresh()` function.
If `order_by` attribute is specified, this function imports from original table
only the new data (not present in projection).

The main advantage of **OOPS** projection mechanism is that it allows to automatically substitute queries on original tables with projections. 
There is `OOPS.auto_substitute_projections` configuration parameter which allows to switch on such substitution.
By default it is switched off, because OOPS projects may be not synchronized with original table and query on projection may return different result.
Right now projections can be automatically substituted only if:
1. Query doesn't contain joins.
2. Query performs aggregation of vector (tile) columns.
3. All other expressions in target list, `ORDER BY` / `GROUP BY` clauses refers only to scalar attributes of projection.

Example of using projections:
create extension OOPS;
create table lineitem(
l_orderkey integer,
l_partkey integer,
l_suppkey integer,
l_linenumber integer,
l_quantity real,
l_extendedprice real,
l_discount real,
l_tax real,
l_returnflag "char",
l_linestatus "char",
l_shipdate date,
l_commitdate date,
l_receiptdate date,
l_shipinstruct char(25),
l_shipmode char(10),
l_comment char(44),
l_dummy char(1));
select
create_projection('OOPS_lineitem','lineitem',array['l_shipdate','l_quantity','l_ext
endedprice','l_discount','l_tax'],array['l_returnflag','l_linestatus']);
\timing
copy lineitem from '/mnt/data/lineitem.tbl' delimiter '|' csv;
select OOPS_lineitem_refresh();
select
l_returnflag,
l_linestatus,
sum(l_quantity) as sum_qty,
sum(l_extendedprice) as sum_base_price,
sum(l_extendedprice*(1-l_discount)) as sum_disc_price,
sum(l_extendedprice*(1-l_discount)*(1+l_tax)) as sum_charge,
avg(l_quantity) as avg_qty,
avg(l_extendedprice) as avg_price,
avg(l_discount) as avg_disc,
count(*) as count_order
from
lineitem
where
l_shipdate <= '1998-12-01'
group by
l_returnflag,
l_linestatus
order by
l_returnflag,
l_linestatus;
set OOPS.auto_substitute_projections TO on;
select
l_returnflag,
l_linestatus,
sum(l_quantity) as sum_qty,
sum(l_extendedprice) as sum_base_price,
sum(l_extendedprice*(1-l_discount)) as sum_disc_price,
sum(l_extendedprice*(1-l_discount)*(1+l_tax)) as sum_charge,
avg(l_quantity) as avg_qty,
avg(l_extendedprice) as avg_price,
avg(l_discount) as avg_disc,
count(*) as count_order
from
lineitem
where
l_shipdate <= '1998-12-01'
group by
l_returnflag,
l_linestatus
order by
l_returnflag,
l_linestatus;