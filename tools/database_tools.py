
import re
from typing import Optional, Any

import sqlglot
from sqlglot import exp
from sqlalchemy import text
from langchain_core.tools import tool

from database.connection import read_engine
from config.settings import settings


# =========================================
# HELPER FUNCTIONS
# =========================================

def _resolve_schema(schema_name: Optional[str] = None) -> str:
    """Resolve database name, defaulting to configured database."""

    schema = schema_name or settings.DB_NAME

    if not schema or not schema.strip():
        raise ValueError("Database/schema name cannot be empty.")

    return schema.strip()


def _parse_single_select(sql_query: str):
    """
    Parse exactly one read-only SELECT statement using
    the MySQL SQL dialect.
    """

    if not sql_query or not sql_query.strip():
        raise ValueError("SQL query cannot be empty.")

    try:
        statements = [
            statement
            for statement in sqlglot.parse(
                sql_query,
                read="mysql"
            )
            if statement is not None
        ]
    except Exception as error:
        raise ValueError(f"SQL parsing failed: {error}")

    if len(statements) != 1:
        raise ValueError(
            "Only one SQL statement is allowed."
        )

    tree = statements[0]

    if not isinstance(tree, exp.Select):
        raise ValueError(
            "Only SELECT queries are allowed."
        )

    # Reject statements with potentially unsafe SELECT clauses.
    if re.search(
        r"\bINTO\s+(?:OUTFILE|DUMPFILE)\b",
        sql_query,
        flags=re.IGNORECASE
    ):
        raise ValueError(
            "SELECT INTO OUTFILE/DUMPFILE is not allowed."
        )

    if re.search(
        r"\bFOR\s+(?:UPDATE|SHARE)\b"
        r"|\bLOCK\s+IN\s+SHARE\s+MODE\b",
        sql_query,
        flags=re.IGNORECASE
    ):
        raise ValueError(
            "Locking SELECT queries are not allowed."
        )

    return tree


def _unique(values: list[str]) -> list[str]:
    """Remove duplicate values while preserving order."""

    return list(dict.fromkeys(
        value for value in values if value
    ))


# =========================================
# TOOL 1: PARSE SQL
# =========================================

@tool
def parse_sql(sql_query: str) -> dict:
    """
    Parse a SQL SELECT query and identify its tables,
    columns, WHERE, JOIN, ORDER BY, GROUP BY, and LIMIT.

    Args:
        sql_query: SQL query to analyze.
    """

    try:
        tree = _parse_single_select(sql_query)

        # Extract tables
        tables = []

        for table in tree.find_all(exp.Table):
            alias_node = table.args.get("alias")

            alias = (
                alias_node.this.name
                if alias_node else None
            )

            tables.append({
                "name": table.name,
                "schema": table.db or None,
                "alias": alias
            })

        # Extract selected columns
        selected_columns = [
            column.sql(dialect="mysql")
            for column in tree.expressions
        ]

        # Extract all referenced columns
        all_columns = _unique([
            column.sql(dialect="mysql")
            for column in tree.find_all(exp.Column)
        ])

        # Extract WHERE
        where_node = tree.args.get("where")

        where_clause = (
            where_node.sql(dialect="mysql")
            if where_node else None
        )

        # Extract JOIN
        joins = []

        for join in tree.args.get("joins") or []:
            on_node = join.args.get("on")
            using_node = join.args.get("using")

            side = join.args.get("side")
            kind = join.args.get("kind")

            joins.append({
                "table": join.this.sql(dialect="mysql"),
                "type": " ".join(
                    value for value in [side, kind]
                    if value
                ) or "INNER",
                "condition": (
                    on_node.sql(dialect="mysql")
                    if on_node else None
                ),
                "using": (
                    [
                        column.sql(dialect="mysql")
                        for column in using_node
                    ]
                    if using_node else []
                )
            })

        # Extract ORDER BY
        order_node = tree.args.get("order")

        order_by = (
            [
                item.sql(dialect="mysql")
                for item in order_node.expressions
            ]
            if order_node else []
        )

        # Extract GROUP BY
        group_node = tree.args.get("group")

        group_by = (
            [
                item.sql(dialect="mysql")
                for item in group_node.expressions
            ]
            if group_node else []
        )

        # Extract LIMIT
        limit_node = tree.args.get("limit")

        limit = (
            limit_node.sql(dialect="mysql")
            if limit_node else None
        )

        return {
            "success": True,
            "query_type": "SELECT",
            "tables": tables,
            "selected_columns": selected_columns,
            "all_columns": all_columns,
            "where": where_clause,
            "joins": joins,
            "order_by": order_by,
            "group_by": group_by,
            "limit": limit
        }

    except Exception as error:
        return {
            "success": False,
            "error": str(error)
        }


# =========================================
# TOOL 2: VALIDATE SQL
# =========================================

@tool
def validate_sql(sql_query: str) -> dict:
    """
    Validate SQL query parsing and ensure that
    only one read-only SELECT statement is allowed.

    Args:
        sql_query: SQL query to validate.
    """

    try:
        tree = _parse_single_select(sql_query)

        return {
            "valid": True,
            "read_only": True,
            "query_type": "SELECT",
            "message": "Query passed the SQL safety checks."
        }

    except Exception as error:
        return {
            "valid": False,
            "read_only": False,
            "message": str(error)
        }


# =========================================
# TOOL 3: GET TABLE SCHEMA
# =========================================

@tool
def get_table_schema(
    table_name: str,
    schema_name: Optional[str] = None
) -> dict:
    """
    Retrieve table structure, column types,
    primary keys, and foreign keys.

    Args:
        table_name: Name of the table to inspect.
        schema_name: Database/schema name. Defaults to configured database.
    """

    try:
        schema = _resolve_schema(schema_name)

        with read_engine.connect() as connection:

            # Retrieve columns
            column_result = connection.execute(
                text("""
                    SELECT
                        COLUMN_NAME,
                        COLUMN_TYPE,
                        IS_NULLABLE,
                        COLUMN_DEFAULT,
                        COLUMN_KEY,
                        EXTRA
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = :schema_name
                      AND TABLE_NAME = :table_name
                    ORDER BY ORDINAL_POSITION
                """),
                {
                    "schema_name": schema,
                    "table_name": table_name
                }
            )

            column_rows = [
                dict(row)
                for row in column_result.mappings().all()
            ]

            if not column_rows:
                return {
                    "success": False,
                    "error": (
                        f"Table '{table_name}' "
                        f"not found in '{schema}'."
                    )
                }

            # Retrieve primary and foreign key constraints
            constraint_result = connection.execute(
                text("""
                    SELECT
                        COLUMN_NAME,
                        CONSTRAINT_NAME,
                        REFERENCED_TABLE_NAME,
                        REFERENCED_COLUMN_NAME
                    FROM information_schema.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = :schema_name
                      AND TABLE_NAME = :table_name
                      AND (
                          CONSTRAINT_NAME = 'PRIMARY'
                          OR REFERENCED_TABLE_NAME IS NOT NULL
                      )
                    ORDER BY ORDINAL_POSITION
                """),
                {
                    "schema_name": schema,
                    "table_name": table_name
                }
            )

            constraint_rows = [
                dict(row)
                for row in constraint_result.mappings().all()
            ]

        primary_keys = []
        foreign_keys = []

        for row in constraint_rows:

            if row["CONSTRAINT_NAME"] == "PRIMARY":
                primary_keys.append(row["COLUMN_NAME"])

            if row["REFERENCED_TABLE_NAME"]:
                foreign_keys.append({
                    "column": row["COLUMN_NAME"],
                    "referenced_table": row["REFERENCED_TABLE_NAME"],
                    "referenced_column": row["REFERENCED_COLUMN_NAME"]
                })

        for column in column_rows:
            column_name = column["COLUMN_NAME"]

            column["IS_PRIMARY_KEY"] = (
                column_name in primary_keys
            )

            column["IS_FOREIGN_KEY"] = any(
                fk["column"] == column_name
                for fk in foreign_keys
            )

        return {
            "success": True,
            "schema_name": schema,
            "table_name": table_name,
            "columns": column_rows,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys
        }

    except Exception as error:
        return {
            "success": False,
            "error": str(error)
        }


# =========================================
# TOOL 4: GET EXISTING INDEXES
# =========================================

@tool
def get_existing_indexes(
    table_name: str,
    schema_name: Optional[str] = None
) -> dict:
    """
    Retrieve all existing indexes on a database table,
    including index names, columns, uniqueness, and types.

    Args:
        table_name: Name of the table to inspect.
        schema_name: Database/schema name. Defaults to configured database.
    """

    try:
        schema = _resolve_schema(schema_name)

        with read_engine.connect() as connection:

            result = connection.execute(
                text("""
                    SELECT
                        INDEX_NAME,
                        NON_UNIQUE,
                        SEQ_IN_INDEX,
                        COLUMN_NAME,
                        COLLATION,
                        CARDINALITY,
                        SUB_PART,
                        INDEX_TYPE
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = :schema_name
                      AND TABLE_NAME = :table_name
                    ORDER BY INDEX_NAME, SEQ_IN_INDEX
                """),
                {
                    "schema_name": schema,
                    "table_name": table_name
                }
            )

            rows = [
                dict(row)
                for row in result.mappings().all()
            ]

        if not rows:
            return {
                "success": False,
                "error": (
                    f"No indexes found or table "
                    f"'{table_name}' does not exist."
                )
            }

        indexes = {}

        for row in rows:

            index_name = row["INDEX_NAME"]

            if index_name not in indexes:
                indexes[index_name] = {
                    "index_name": index_name,
                    "is_unique": not bool(row["NON_UNIQUE"]),
                    "index_type": row["INDEX_TYPE"],
                    "columns": []
                }

            indexes[index_name]["columns"].append({
                "name": row["COLUMN_NAME"],
                "sequence": row["SEQ_IN_INDEX"],
                "collation": row["COLLATION"],
                "cardinality": row["CARDINALITY"],
                "prefix_length": row["SUB_PART"]
            })

        return {
            "success": True,
            "schema_name": schema,
            "table_name": table_name,
            "total_indexes": len(indexes),
            "indexes": list(indexes.values())
        }

    except Exception as error:
        return {
            "success": False,
            "error": str(error)
        }


# =========================================
# TOOL 5: EXPLAIN QUERY
# =========================================

@tool
def explain_query(sql_query: str) -> dict:
    """
    Execute MySQL EXPLAIN on a validated SELECT query
    and return its execution plan.

    Args:
        sql_query: SELECT query to analyze using EXPLAIN.
    """

    try:
        # Enforce read-only SELECT validation
        _parse_single_select(sql_query)

        clean_query = sql_query.strip().rstrip(";").strip()

        with read_engine.connect() as connection:

            result = connection.exec_driver_sql(
                f"EXPLAIN {clean_query}"
            )

            execution_plan = [
                dict(row)
                for row in result.mappings().all()
            ]

        return {
            "success": True,
            "query": clean_query,
            "execution_plan": execution_plan
        }

    except Exception as error:
        return {
            "success": False,
            "error": str(error)
        }


# =========================================
# TOOL 6: GET TABLE STATISTICS
# =========================================

@tool
def get_table_statistics(
    table_name: str,
    schema_name: Optional[str] = None
) -> dict:
    """
    Retrieve table statistics, including estimated row count,
    storage size, engine, and index cardinality.

    Args:
        table_name: Name of the table to inspect.
        schema_name: Database/schema name. Defaults to configured database.
    """

    try:
        schema = _resolve_schema(schema_name)

        with read_engine.connect() as connection:

            # Retrieve table statistics
            table_result = connection.execute(
                text("""
                    SELECT
                        ENGINE,
                        TABLE_ROWS,
                        AVG_ROW_LENGTH,
                        DATA_LENGTH,
                        INDEX_LENGTH,
                        DATA_FREE,
                        AUTO_INCREMENT,
                        UPDATE_TIME
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = :schema_name
                      AND TABLE_NAME = :table_name
                """),
                {
                    "schema_name": schema,
                    "table_name": table_name
                }
            )

            table_stats = table_result.mappings().one_or_none()

            if table_stats is None:
                return {
                    "success": False,
                    "error": (
                        f"Table '{table_name}' "
                        f"not found in '{schema}'."
                    )
                }

            # Retrieve index cardinality
            index_result = connection.execute(
                text("""
                    SELECT
                        INDEX_NAME,
                        COLUMN_NAME,
                        CARDINALITY
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = :schema_name
                      AND TABLE_NAME = :table_name
                    ORDER BY INDEX_NAME, SEQ_IN_INDEX
                """),
                {
                    "schema_name": schema,
                    "table_name": table_name
                }
            )

            index_stats = [
                dict(row)
                for row in index_result.mappings().all()
            ]

        return {
            "success": True,
            "schema_name": schema,
            "table_name": table_name,
            "statistics": dict(table_stats),
            "index_cardinality": index_stats,
            "note": (
                "TABLE_ROWS and CARDINALITY are estimates, "
                "especially for InnoDB tables."
            )
        }

    except Exception as error:
        return {
            "success": False,
            "error": str(error)
        }


# =========================================
# EXPORT ALL DATABASE TOOLS
# =========================================

database_tools = [
    parse_sql,
    validate_sql,
    get_table_schema,
    get_existing_indexes,
    explain_query,
    get_table_statistics
]
