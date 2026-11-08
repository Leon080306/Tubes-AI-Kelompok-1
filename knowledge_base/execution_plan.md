
# MySQL Execution Plan Interpretation

## 1. What is EXPLAIN?

EXPLAIN displays how MySQL plans to execute
a SQL query.

It helps identify inefficient access methods,
index usage, and estimated rows examined.

Example:

EXPLAIN
SELECT *
FROM orders
WHERE customer_id = 105
ORDER BY created_at DESC
LIMIT 10;

## 2. Important EXPLAIN Columns

### id
Identifies the SELECT operation.

### select_type
Describes the type of SELECT operation.

### table
Identifies the table involved in the execution plan.

### type
Describes the access method.

Common values include:

- system
- const
- eq_ref
- ref
- range
- index
- ALL

ALL indicates a Full Table Scan.

### possible_keys
Lists indexes that the optimizer considers possible.

### key
Indicates the index actually selected by the optimizer.

NULL means no index was selected.

### rows
Estimates the number of rows the database expects
to examine.

### Extra
Provides additional execution information.

Examples:

- Using where
- Using index
- Using filesort
- Using temporary

## 3. Full Table Scan

A Full Table Scan occurs when the database
examines all rows in a table.

It is represented by:

type = ALL

This may become expensive when the table
contains a large number of records.

## 4. Using Filesort

Using filesort indicates that the database
uses an additional sorting operation.

It does not necessarily mean that MySQL
creates a physical file on disk.

## 5. Index Optimization

A query may benefit from an index when
the current execution plan performs
unnecessary table scanning or sorting.

However, the optimizer may still choose
a table scan when it estimates that scanning
is cheaper than using an index.

## 6. Optimization Verification

After creating a recommended index:

1. Run EXPLAIN again.
2. Check the key column.
3. Inspect the type column.
4. Compare estimated rows.
5. Review the Extra column.

Do not evaluate optimization based only
on whether an index exists.

The actual execution plan must be examined.
