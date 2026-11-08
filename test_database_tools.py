
import json

from tools.database_tools import (
    parse_sql,
    validate_sql,
    get_table_schema,
    get_existing_indexes,
    explain_query,
    get_table_statistics
)


# =========================================
# SAMPLE SQL QUERY
# =========================================

sample_query = """
SELECT *
FROM orders
WHERE customer_id = 105
ORDER BY created_at DESC
LIMIT 10;
"""


def test_tool(name, tool, parameters):
    print("\n" + "=" * 60)
    print(f"TESTING: {name}")
    print("=" * 60)

    result = tool.invoke(parameters)

    print(json.dumps(
        result,
        indent=4,
        default=str
    ))

    return result


if __name__ == "__main__":

    # TOOL 1
    test_tool(
        "parse_sql",
        parse_sql,
        {
            "sql_query": sample_query
        }
    )

    # TOOL 2
    test_tool(
        "validate_sql",
        validate_sql,
        {
            "sql_query": sample_query
        }
    )

    # TOOL 3
    test_tool(
        "get_table_schema",
        get_table_schema,
        {
            "table_name": "orders"
        }
    )

    # TOOL 4
    test_tool(
        "get_existing_indexes",
        get_existing_indexes,
        {
            "table_name": "orders"
        }
    )

    # TOOL 5
    test_tool(
        "explain_query",
        explain_query,
        {
            "sql_query": sample_query
        }
    )

    # TOOL 6
    test_tool(
        "get_table_statistics",
        get_table_statistics,
        {
            "table_name": "orders"
        }
    )

    print("\nAll database tool tests completed.")
