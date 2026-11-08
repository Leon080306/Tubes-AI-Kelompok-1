
import json

from tools.rag_tools import (
    search_knowledge_base,
    rewrite_search_query
)


# =========================================
# TEST 1: NORMAL KNOWLEDGE BASE SEARCH
# =========================================

def test_normal_search():

    print("\n" + "=" * 60)
    print("TEST 1: KNOWLEDGE BASE SEARCH")
    print("=" * 60)

    result = search_knowledge_base.invoke({
        "query": (
            "MySQL composite index for equality filtering "
            "and ORDER BY optimization"
        ),
        "top_k": 3,
        "category": "indexing"
    })

    print(json.dumps(
        result,
        indent=4,
        ensure_ascii=False
    ))

    return result


# =========================================
# TEST 2: SEARCH NOT_FOUND
# =========================================

def test_not_found():

    print("\n" + "=" * 60)
    print("TEST 2: SEARCH NOT_FOUND")
    print("=" * 60)

    result = search_knowledge_base.invoke({
        "query": "Optimize customer orders query",
        "top_k": 3,
        "category": "nonexistent_category"
    })

    print(json.dumps(
        result,
        indent=4,
        ensure_ascii=False
    ))

    return result


# =========================================
# TEST 3: QUERY REWRITING
# =========================================

def test_query_rewriting(original_query):

    print("\n" + "=" * 60)
    print("TEST 3: QUERY REWRITING")
    print("=" * 60)

    result = rewrite_search_query.invoke({
        "original_query": original_query,
        "failure_reason": (
            "The first search returned NOT_FOUND."
        ),
        "sql_context": """
            SELECT *
            FROM orders
            WHERE customer_id = 105
            ORDER BY created_at DESC
            LIMIT 10;

            The query has a WHERE condition on customer_id
            and an ORDER BY condition on created_at.
        """
    })

    print(json.dumps(
        result,
        indent=4,
        ensure_ascii=False
    ))

    return result


# =========================================
# TEST 4: RETRY SEARCH
# =========================================

def test_retry_search(rewritten_query):

    print("\n" + "=" * 60)
    print("TEST 4: RETRY KNOWLEDGE BASE SEARCH")
    print("=" * 60)

    result = search_knowledge_base.invoke({
        "query": rewritten_query,
        "top_k": 3,
        "category": "indexing"
    })

    print(json.dumps(
        result,
        indent=4,
        ensure_ascii=False
    ))

    return result


# =========================================
# MAIN
# =========================================

if __name__ == "__main__":

    # Test normal semantic search
    normal_result = test_normal_search()

    # Simulate a failed search
    failed_result = test_not_found()

    # Trigger rewriting only when NOT_FOUND
    if failed_result.get("status") == "NOT_FOUND":

        rewrite_result = test_query_rewriting(
            original_query="Optimize customer orders query"
        )

        if rewrite_result.get("success"):

            # Retry with rewritten query
            retry_result = test_retry_search(
                rewrite_result["rewritten_query"]
            )

            print("\nFINAL RAG STATUS:")
            print(retry_result.get("status"))

        else:
            print("\nQuery rewriting failed.")

    else:
        print("\nNOT_FOUND was not triggered.")

    print("\nRAG TESTING COMPLETED.")
