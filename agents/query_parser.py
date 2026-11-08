
from tools.database_tools import (
    parse_sql,
    validate_sql,
    get_table_schema,
    get_existing_indexes,
    explain_query,
    get_table_statistics
)


# =========================================
# QUERY PARSER WORKER
# =========================================

def query_parser_worker(state: dict) -> dict:
    """
    Analyze the user's SQL query and retrieve
    database information using six analysis tools.
    """

    sql_query = state.get("sql_query", "")

    trace = []

    def record(thought, action, parameters, observation):

        trace.append({
            "worker": "Query Parser Worker",
            "thought": thought,
            "action": action,
            "parameters": parameters,
            "observation": observation
        })

    try:

        # =================================
        # ACTION 1: VALIDATE SQL
        # =================================

        validation = validate_sql.invoke({
            "sql_query": sql_query
        })

        record(
            thought="Ensure the submitted SQL is valid and read-only.",
            action="validate_sql",
            parameters={
                "sql_query": sql_query
            },
            observation=validation
        )

        if not validation.get("valid"):

            return {
                "sql_validation": validation,
                "error": validation.get("message"),
                "next_worker": "END",
                "trace": trace
            }

        # =================================
        # ACTION 2: PARSE SQL
        # =================================

        parsed_query = parse_sql.invoke({
            "sql_query": sql_query
        })

        record(
            thought="Identify the tables and SQL clauses involved in the query.",
            action="parse_sql",
            parameters={
                "sql_query": sql_query
            },
            observation=parsed_query
        )

        if not parsed_query.get("success"):

            return {
                "error": parsed_query.get("error"),
                "next_worker": "END",
                "trace": trace
            }

        tables = parsed_query.get("tables", [])

        if not tables:

            return {
                "error": "No database tables were identified.",
                "next_worker": "END",
                "trace": trace
            }

        # =================================
        # ACTION 3-5: DATABASE INSPECTION
        # =================================

        table_analyses = {}

        for table in tables:

            table_name = table["name"]
            schema_name = table.get("schema")

            parameters = {
                "table_name": table_name
            }

            if schema_name:
                parameters["schema_name"] = schema_name

            # Get table schema
            schema_result = get_table_schema.invoke(
                parameters
            )

            record(
                thought=f"Inspect the structure of table {table_name}.",
                action="get_table_schema",
                parameters=parameters,
                observation=schema_result
            )

            if not schema_result.get("success"):

                return {
                    "error": schema_result.get("error"),
                    "next_worker": "END",
                    "trace": trace
                }

            # Get existing indexes
            index_result = get_existing_indexes.invoke(
                parameters
            )

            record(
                thought=f"Check existing indexes on table {table_name}.",
                action="get_existing_indexes",
                parameters=parameters,
                observation=index_result
            )

            if not index_result.get("success"):

                return {
                    "error": index_result.get("error"),
                    "next_worker": "END",
                    "trace": trace
                }

            # Get table statistics
            statistics_result = get_table_statistics.invoke(
                parameters
            )

            record(
                thought=f"Retrieve table statistics for {table_name}.",
                action="get_table_statistics",
                parameters=parameters,
                observation=statistics_result
            )

            if not statistics_result.get("success"):

                return {
                    "error": statistics_result.get("error"),
                    "next_worker": "END",
                    "trace": trace
                }

            table_analyses[table_name] = {
                "schema": schema_result,
                "existing_indexes": index_result,
                "statistics": statistics_result
            }

        # =================================
        # ACTION 6: EXPLAIN QUERY
        # =================================

        execution_plan = explain_query.invoke({
            "sql_query": sql_query
        })

        record(
            thought="Examine the database execution plan to identify performance issues.",
            action="explain_query",
            parameters={
                "sql_query": sql_query
            },
            observation=execution_plan
        )

        if not execution_plan.get("success"):

            return {
                "error": execution_plan.get("error"),
                "next_worker": "END",
                "trace": trace
            }

        # =================================
        # PREPARE SHARED STATE
        # =================================

        # The initial implementation uses the first
        # referenced table as the index recommendation target.

        primary_table = tables[0]["name"]

        primary_analysis = table_analyses[primary_table]

        print("\n[QUERY PARSER WORKER] Completed successfully.")

        return {
            "sql_validation": validation,
            "parsed_query": parsed_query,

            "table_analyses": table_analyses,

            "table_schema": primary_analysis["schema"],

            "existing_indexes": (
                primary_analysis["existing_indexes"]
            ),

            "table_statistics": (
                primary_analysis["statistics"]
            ),

            "execution_plan": execution_plan,

            "next_worker": "database_specialist",

            "trace": trace
        }

    except Exception as error:

        return {
            "error": str(error),
            "next_worker": "END",
            "trace": trace
        }
