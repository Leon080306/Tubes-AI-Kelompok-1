
import re
from typing import Optional

from langchain_core.tools import tool
from sqlalchemy import text

from database.connection import read_engine, dba_engine
from config.settings import settings


# =========================================
# HELPER: PARSE CREATE INDEX SQL
# =========================================

IDENTIFIER = r"`?[A-Za-z_][A-Za-z0-9_$]*`?"


def _parse_create_index(create_index_sql: str) -> dict:
    """
    Parse a simple CREATE INDEX statement.

    Only regular CREATE INDEX statements are accepted.
    """

    if not create_index_sql or not create_index_sql.strip():
        raise ValueError("CREATE INDEX SQL cannot be empty.")

    sql = create_index_sql.strip()

    if sql.endswith(";"):
        sql = sql[:-1].strip()

    pattern = re.compile(
        rf"""
        CREATE\s+INDEX\s+
        (?P<index_name>{IDENTIFIER})
        \s+ON\s+
        (?:(?P<schema_name>{IDENTIFIER})\s*\.\s*)?
        (?P<table_name>{IDENTIFIER})
        \s*\((?P<columns>[^()]*)\)
        """,
        re.IGNORECASE | re.VERBOSE | re.DOTALL
    )

    match = pattern.fullmatch(sql)

    if not match:
        raise ValueError(
            "Invalid SQL. Only simple CREATE INDEX "
            "statements are supported."
        )

    def clean_identifier(value):
        return value.strip("`")

    index_name = clean_identifier(
        match.group("index_name")
    )

    schema_name = match.group("schema_name")

    if schema_name:
        schema_name = clean_identifier(schema_name)

    table_name = clean_identifier(
        match.group("table_name")
    )

    # Parse index columns
    index_columns = []

    column_parts = match.group("columns").split(",")

    for part in column_parts:

        column_match = re.fullmatch(
            rf"\s*(?P<name>{IDENTIFIER})"
            r"\s*(?P<direction>ASC|DESC)?\s*",
            part,
            re.IGNORECASE
        )

        if not column_match:
            raise ValueError(
                f"Invalid index column expression: {part}"
            )

        index_columns.append({
            "name": clean_identifier(
                column_match.group("name")
            ),
            "direction": (
                column_match.group("direction") or "ASC"
            ).upper()
        })

    if not index_columns:
        raise ValueError("No index columns specified.")

    if len(index_columns) > 16:
        raise ValueError(
            "Index exceeds the configured 16-column safety limit."
        )

    column_names = [
        column["name"].lower()
        for column in index_columns
    ]

    if len(column_names) != len(set(column_names)):
        raise ValueError("Duplicate columns are not allowed.")

    return {
        "index_name": index_name,
        "schema_name": schema_name,
        "table_name": table_name,
        "columns": index_columns
    }


# =========================================
# HELPER: VALIDATE INDEX AGAINST DATABASE
# =========================================

def _prepare_index_execution(create_index_sql: str) -> dict:
    """
    Validate the requested index against the actual
    database schema and construct a safe SQL statement.
    """

    parsed = _parse_create_index(create_index_sql)

    schema = settings.DB_NAME

    if (
        parsed["schema_name"]
        and parsed["schema_name"].lower() != schema.lower()
    ):
        raise ValueError(
            "Creating indexes outside the configured database "
            "is not allowed."
        )

    table_name = parsed["table_name"]
    index_name = parsed["index_name"]
    candidate_columns = parsed["columns"]

    with read_engine.connect() as connection:

        # ---------------------------------
        # Check table and available columns
        # ---------------------------------

        column_result = connection.execute(
            text("""
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = :schema_name
                  AND TABLE_NAME = :table_name
            """),
            {
                "schema_name": schema,
                "table_name": table_name
            }
        )

        available_columns = {
            row["COLUMN_NAME"].lower()
            for row in column_result.mappings().all()
        }

        if not available_columns:
            raise ValueError(
                f"Table '{table_name}' does not exist."
            )

        for column in candidate_columns:

            if column["name"].lower() not in available_columns:
                raise ValueError(
                    f"Column '{column['name']}' "
                    f"does not exist in table '{table_name}'."
                )

        # ---------------------------------
        # Retrieve existing indexes
        # ---------------------------------

        index_result = connection.execute(
            text("""
                SELECT
                    INDEX_NAME,
                    SEQ_IN_INDEX,
                    COLUMN_NAME
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

        index_rows = [
            dict(row)
            for row in index_result.mappings().all()
        ]

    # ---------------------------------
    # Check duplicate index name
    # ---------------------------------

    existing_names = {
        row["INDEX_NAME"].lower()
        for row in index_rows
    }

    if index_name.lower() in existing_names:
        raise ValueError(
            f"Index '{index_name}' already exists."
        )

    # ---------------------------------
    # Check redundant indexes
    # ---------------------------------

    existing_indexes = {}

    for row in index_rows:

        existing_indexes.setdefault(
            row["INDEX_NAME"],
            []
        ).append(row["COLUMN_NAME"].lower())

    new_columns = [
        column["name"].lower()
        for column in candidate_columns
    ]

    for existing_name, existing_columns in existing_indexes.items():

        if (
            len(existing_columns) >= len(new_columns)
            and existing_columns[:len(new_columns)] == new_columns
        ):
            raise ValueError(
                f"Proposed index is already covered by "
                f"existing index '{existing_name}'."
            )

    # ---------------------------------
    # Rebuild SQL using validated identifiers
    # ---------------------------------

    quoted_columns = []

    for column in candidate_columns:

        quoted = f"`{column['name']}`"

        if column["direction"] == "DESC":
            quoted += " DESC"

        quoted_columns.append(quoted)

    safe_sql = (
        f"CREATE INDEX `{index_name}` "
        f"ON `{schema}`.`{table_name}` "
        f"({', '.join(quoted_columns)})"
    )

    return {
        "sql": safe_sql,
        "index_name": index_name,
        "table_name": table_name,
        "schema_name": schema,
        "columns": candidate_columns
    }


# =========================================
# TOOL 11: EXECUTE CREATE INDEX
# =========================================

@tool
def execute_create_index(create_index_sql: str) -> dict:
    """
    Execute a validated CREATE INDEX statement using
    the DBA database connection.

    IMPORTANT:
    This tool must only be called by the protected
    LangGraph Execute Index Node after DBA approval.

    It must never be exposed directly to an LLM.
    """

    try:

        # Revalidate the statement immediately before execution
        prepared = _prepare_index_execution(
            create_index_sql
        )

        # DDL is executed in AUTOCOMMIT mode.
        # CREATE INDEX is not rollbackable.
        with dba_engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as connection:

            connection.exec_driver_sql(
                prepared["sql"]
            )

        return {
            "success": True,
            "status": "EXECUTED",
            "index_name": prepared["index_name"],
            "table_name": prepared["table_name"],
            "schema_name": prepared["schema_name"],
            "columns": prepared["columns"],
            "executed_sql": prepared["sql"],
            "message": "Index created successfully."
        }

    except Exception as error:

        return {
            "success": False,
            "status": "FAILED",
            "error": str(error)
        }


# =========================================
# TOOL 12: VERIFY INDEX CREATION
# =========================================

@tool
def verify_index_creation(
    table_name: str,
    index_name: str,
    schema_name: Optional[str] = None
) -> dict:
    """
    Verify whether an index exists in the database.

    Args:
        table_name: Name of the table containing the index.
        index_name: Name of the index to verify.
        schema_name: Database/schema name. Defaults to the configured database.
    """

    try:

        schema = schema_name or settings.DB_NAME

        if schema.lower() != settings.DB_NAME.lower():
            return {
                "success": False,
                "status": "ERROR",
                "message": "Access to other databases is not allowed."
            }

        with read_engine.connect() as connection:

            # Check whether the table exists
            table_result = connection.execute(
                text("""
                    SELECT TABLE_NAME
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = :schema_name
                      AND TABLE_NAME = :table_name
                """),
                {
                    "schema_name": schema,
                    "table_name": table_name
                }
            )

            if table_result.first() is None:
                return {
                    "success": False,
                    "status": "TABLE_NOT_FOUND",
                    "message": f"Table '{table_name}' not found."
                }

            # Retrieve requested index
            result = connection.execute(
                text("""
                    SELECT
                        INDEX_NAME,
                        NON_UNIQUE,
                        SEQ_IN_INDEX,
                        COLUMN_NAME,
                        INDEX_TYPE,
                        CARDINALITY
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = :schema_name
                      AND TABLE_NAME = :table_name
                      AND INDEX_NAME = :index_name
                    ORDER BY SEQ_IN_INDEX
                """),
                {
                    "schema_name": schema,
                    "table_name": table_name,
                    "index_name": index_name
                }
            )

            rows = [
                dict(row)
                for row in result.mappings().all()
            ]

        if not rows:
            return {
                "success": True,
                "status": "NOT_FOUND",
                "table_name": table_name,
                "index_name": index_name,
                "message": "Index has not been created."
            }

        # Build index information
        index_info = {
            "index_name": rows[0]["INDEX_NAME"],
            "table_name": table_name,
            "schema_name": schema,
            "is_unique": not bool(rows[0]["NON_UNIQUE"]),
            "index_type": rows[0]["INDEX_TYPE"],
            "columns": [
                {
                    "name": row["COLUMN_NAME"],
                    "sequence": row["SEQ_IN_INDEX"],
                    "cardinality": row["CARDINALITY"]
                }
                for row in rows
            ]
        }

        return {
            "success": True,
            "status": "VERIFIED",
            "index": index_info,
            "message": "Index successfully verified."
        }

    except Exception as error:

        return {
            "success": False,
            "status": "ERROR",
            "message": str(error)
        }


# =========================================
# EXPORT EXECUTION TOOLS
# =========================================

execution_tools = [
    execute_create_index,
    verify_index_creation
]
