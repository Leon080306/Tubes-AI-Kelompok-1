
# MySQL Composite Index Guidelines

## 1. What is a Composite Index?

A Composite Index is an index created using
two or more columns in a specific order.

Example:

CREATE INDEX idx_customer_created
ON orders (customer_id, created_at);

This index contains customer_id as the first column
and created_at as the second column.

## 2. Column Order Matters

MySQL composite indexes follow the leftmost-prefix principle.

An index on (customer_id, created_at) can support queries
that use:

- customer_id
- customer_id and created_at together

It is not generally equivalent to having
a separate index on created_at.

## 3. Equality Filtering and Sorting

Consider this query:

SELECT *
FROM orders
WHERE customer_id = 105
ORDER BY created_at DESC
LIMIT 10;

A possible index recommendation is:

CREATE INDEX idx_orders_customer_created
ON orders (customer_id, created_at);

The equality condition on customer_id comes first,
followed by created_at for sorting.

The database may use this index for filtering
and retrieving records in the required order.

## 4. Avoid Redundant Indexes

Before creating a Composite Index,
inspect the existing indexes.

For example, an existing index on
(customer_id, created_at) may already support
queries filtering by customer_id.

Creating another index on customer_id alone
may be redundant depending on workload requirements.

## 5. Index Direction

MySQL supports ascending and descending index definitions.

The optimizer may also perform backward index scans.

Do not assume a DESC index is always necessary
for an ORDER BY created_at DESC query.

Evaluate the actual execution plan.

## 6. Important Considerations

Composite index recommendations should consider:

- WHERE conditions
- JOIN conditions
- ORDER BY columns
- GROUP BY columns
- Existing indexes
- Column selectivity
- Storage requirements
- INSERT and UPDATE overhead

Always validate the actual performance
using EXPLAIN after creating an index.
