
# MySQL Indexing Best Practices

## 1. What is Database Indexing?

Database indexing is a technique used to improve data retrieval
performance by creating an organized structure that helps the
database locate records without scanning every row.

MySQL commonly uses B-Tree indexes for standard index operations.

## 2. When Should Indexes Be Created?

Indexes are useful for columns frequently used in:

- WHERE conditions
- JOIN conditions
- ORDER BY clauses
- GROUP BY clauses

However, not every column needs an index.

Indexes should be created based on actual query patterns
and execution plan analysis.

## 3. Primary Key Index

A Primary Key automatically creates a unique index.

It ensures that every record can be uniquely identified.

Avoid creating another index that duplicates
an existing Primary Key index.

## 4. Index Selectivity

Selectivity describes how effectively an index narrows down
the number of matching rows.

Columns with higher selectivity are generally better
candidates for indexing.

For example, a customer_id column may be useful
when queries frequently filter orders by customer.

## 5. Index Maintenance Cost

Indexes require additional storage.

They also introduce overhead during INSERT, UPDATE,
and DELETE operations because indexes may need to be updated.

Too many indexes can reduce write performance.

## 6. Index Recommendation Guidelines

Before recommending a new index:

1. Inspect the existing indexes.
2. Examine query filtering and sorting conditions.
3. Analyze the execution plan.
4. Check column selectivity and table statistics.
5. Avoid duplicate or redundant indexes.
6. Consider write-performance overhead.

An index recommendation should always be supported
by actual query patterns and database statistics.
