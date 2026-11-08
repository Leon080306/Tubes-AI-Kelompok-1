
import json

from tools.database_tools import (
    get_table_schema,
    get_existing_indexes,
    explain_query
)

from tools.rag_tools import search_knowledge_base

from tools.optimization_tools import (
    generate_index_recommendation,
    validate_index_recommendation
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


# =========================================
# HELPER: PRINT RESULT
# =========================================

def print_result(title, result):

    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    print(json.dumps(
        result,
        indent=4,
        ensure_ascii=False,
        default=str
    ))


# =========================================
# TEST 1: GET DATABASE INFORMATION
# =========================================

def test_database_analysis():

    print("\n[1] Collecting database information...")

    schema = get_table_schema.invoke({
        "table_name": "orders"
    })

    indexes = get_existing_indexes.invoke({
        "table_name": "orders"
    })

    execution_plan = explain_query.invoke({
        "sql_query": sample_query
    })

    print_result("TABLE SCHEMA", schema)
    print_result("EXISTING INDEXES", indexes)
    print_result("EXECUTION PLAN", execution_plan)

    if not schema.get("success"):
        raise RuntimeError("Failed to retrieve table schema.")

    if not indexes.get("success"):
        raise RuntimeError("Failed to retrieve existing indexes.")

    if not execution_plan.get("success"):
        raise RuntimeError("Failed to retrieve execution plan.")

    return schema, indexes, execution_plan


# =========================================
# TEST 2: GET KNOWLEDGE CONTEXT
# =========================================

def test_knowledge_retrieval():

    print("\n[2] Retrieving Knowledge Base documents...")

    result = search_knowledge_base.invoke({
        "query": (
            "MySQL composite index for filtering "
            "customer_id and sorting created_at DESC"
        ),
        "top_k": 3,
        "category": "indexing"
    })

    print_result("KNOWLEDGE BASE RESULT", result)

    if result.get("status") != "FOUND":
        raise RuntimeError(
            "Failed to retrieve relevant Knowledge Base documents."
        )

    knowledge_context = "\n\n".join(
        (
            f"Source: {item['source']}\n"
            f"Content: {item['content']}"
        )
        for item in result["results"]
    )

    return knowledge_context


# =========================================
# TEST 3: GENERATE INDEX RECOMMENDATION
# =========================================

def test_generate_recommendation(
    schema,
    indexes,
    execution_plan,
    knowledge_context
):

    print("\n[3] Generating index recommendation...")

    result = generate_index_recommendation.invoke({

        "sql_query": sample_query,

        "execution_plan": execution_plan,

        "table_schema": schema,

        "existing_indexes": indexes,

        "knowledge_context": knowledge_context

    })

    print_result("INDEX RECOMMENDATION", result)

    return result


# =========================================
# TEST 4: VALIDATE INDEX RECOMMENDATION
# =========================================

def test_validate_recommendation(
    recommendation,
    schema,
    indexes
):

    print("\n[4] Validating index recommendation...")

    if recommendation.get("status") != "RECOMMENDED":

        print(
            "No valid index recommendation was generated."
        )

        return None

    recommendation_data = recommendation["recommendation"]

    result = validate_index_recommendation.invoke({

        "create_index_sql": (
            recommendation_data["create_index_sql"]
        ),

        "table_schema": schema,

        "existing_indexes": indexes

    })

    print_result("VALIDATION RESULT", result)

    return result


# =========================================
# TEST 5: TEST INVALID INDEX
# =========================================

def test_invalid_index(schema, indexes):

    print("\n[5] Testing invalid index recommendation...")

    result = validate_index_recommendation.invoke({

        "create_index_sql": """
            CREATE INDEX idx_invalid
            ON orders (unknown_column)
        """,

        "table_schema": schema,

        "existing_indexes": indexes

    })

    print_result("INVALID INDEX RESULT", result)

    return result


# =========================================
# MAIN
# =========================================

if __name__ == "__main__":

    # Step 1: Collect actual database information
    schema, indexes, execution_plan = (
        test_database_analysis()
    )

    # Step 2: Retrieve Knowledge Base documents
    knowledge_context = test_knowledge_retrieval()

    # Step 3: Ask Qwen to generate an index recommendation
    recommendation = test_generate_recommendation(
        schema,
        indexes,
        execution_plan,
        knowledge_context
    )

    # Step 4: Validate generated recommendation
    if recommendation.get("status") == "RECOMMENDED":

        validation = test_validate_recommendation(
            recommendation,
            schema,
            indexes
        )

    else:
        validation = None

    # Step 5: Verify that invalid columns are rejected
    invalid_result = test_invalid_index(
        schema,
        indexes
    )

    print("\n" + "=" * 60)
    print("OPTIMIZATION TOOLS TESTING COMPLETED")
    print("=" * 60)

    print(
        "Recommendation:",
        recommendation.get("status")
    )

    print(
        "Generated Index Valid:",
        validation.get("valid")
        if validation else "Not Generated"
    )

    print(
        "Invalid Index Rejected:",
        invalid_result.get("valid") is False
    )
