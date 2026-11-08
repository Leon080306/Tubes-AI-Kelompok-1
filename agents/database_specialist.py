
from tools.rag_tools import (
    search_knowledge_base,
    rewrite_search_query
)


# =========================================
# DATABASE SPECIALIST WORKER
# =========================================

def database_specialist_worker(state: dict) -> dict:
    """
    Search the Knowledge Base for relevant SQL
    optimization guidelines.

    If the initial search returns NOT_FOUND,
    rewrite the query and retry exactly once.
    """

    # =====================================
    # RETRIEVE SHARED STATE
    # =====================================

    parsed_query = state.get("parsed_query", {})

    sql_query = state.get("sql_query", "")

    execution_plan = state.get("execution_plan", {})

    trace = []

    rewritten_query = None

    # =====================================
    # HELPER: RECORD REACT TRACE
    # =====================================

    def record(thought, action, parameters, observation):

        trace.append({
            "worker": "Database Specialist Worker",
            "thought": thought,
            "action": action,
            "parameters": parameters,
            "observation": observation
        })

    try:

        # =================================
        # PREPARE SEARCH QUERY
        # =================================

        tables = [
            table["name"]
            for table in parsed_query.get("tables", [])
        ]

        where_clause = (
            parsed_query.get("where") or "None"
        )

        order_by = parsed_query.get("order_by", [])

        join_conditions = parsed_query.get("joins", [])

        search_query = (
            "MySQL indexing best practices for "
            f"tables {', '.join(tables)}. "
            f"Filtering condition: {where_clause}. "
            f"Sorting condition: {', '.join(order_by) or 'None'}. "
            f"Join conditions: {join_conditions}."
        )

        # =================================
        # ACTION 1: INITIAL RAG SEARCH
        # =================================

        search_parameters = {
            "query": search_query,
            "top_k": 3,
            "category": "indexing"
        }

        search_result = search_knowledge_base.invoke(
            search_parameters
        )

        record(
            thought=(
                "Find indexing best practices relevant "
                "to the analyzed SQL query."
            ),
            action="search_knowledge_base",
            parameters=search_parameters,
            observation=search_result
        )

        # =================================
        # CHECK INITIAL SEARCH STATUS
        # =================================

        search_status = search_result.get("status")

        # Handle technical errors
        if search_status == "ERROR":

            return {
                "rag_result": search_result,
                "error": search_result.get("message"),
                "next_worker": "END",
                "trace": trace
            }

        # Handle unexpected status
        if search_status not in ["FOUND", "NOT_FOUND"]:

            return {
                "rag_result": search_result,
                "error": "Unexpected Knowledge Base search status.",
                "next_worker": "END",
                "trace": trace
            }

        # =================================
        # ACTION 2: QUERY REWRITING
        # =================================

        if search_status == "NOT_FOUND":

            print(
                "\n[DATABASE SPECIALIST] "
                "NOT_FOUND detected. Rewriting query..."
            )

            sql_context = f"""
SQL QUERY:
{sql_query}

PARSED QUERY:
{parsed_query}

EXECUTION PLAN:
{execution_plan}
"""

            rewrite_parameters = {
                "original_query": search_query,
                "failure_reason": (
                    "The initial Knowledge Base search "
                    "returned NOT_FOUND."
                ),
                "sql_context": sql_context
            }

            rewrite_result = rewrite_search_query.invoke(
                rewrite_parameters
            )

            record(
                thought=(
                    "The initial search failed. "
                    "Rewrite the search query using SQL "
                    "and execution plan context."
                ),
                action="rewrite_search_query",
                parameters=rewrite_parameters,
                observation=rewrite_result
            )

            # Check rewriting result
            if not rewrite_result.get("success"):

                return {
                    "error": (
                        "Knowledge Base query rewriting failed: "
                        + rewrite_result.get(
                            "error",
                            "Unknown rewriting error."
                        )
                    ),
                    "next_worker": "END",
                    "trace": trace
                }

            rewritten_query = rewrite_result.get(
                "rewritten_query"
            )

            if not rewritten_query:

                return {
                    "error": "Rewritten query is empty.",
                    "next_worker": "END",
                    "trace": trace
                }

            # =================================
            # ACTION 3: RETRY RAG SEARCH
            # =================================

            retry_parameters = {
                "query": rewritten_query,
                "top_k": 3,
                "category": "indexing"
            }

            retry_result = search_knowledge_base.invoke(
                retry_parameters
            )

            record(
                thought=(
                    "Search the Knowledge Base again "
                    "using the rewritten query."
                ),
                action="search_knowledge_base",
                parameters=retry_parameters,
                observation=retry_result
            )

            retry_status = retry_result.get("status")

            # Handle technical errors
            if retry_status == "ERROR":

                return {
                    "rag_result": retry_result,
                    "rewritten_query": rewritten_query,
                    "error": (
                        "Knowledge Base retry encountered "
                        "a technical error: "
                        + retry_result.get(
                            "message",
                            "Unknown search error."
                        )
                    ),
                    "next_worker": "END",
                    "trace": trace
                }

            # Retry only once
            if retry_status != "FOUND":

                return {
                    "rag_result": retry_result,
                    "rewritten_query": rewritten_query,
                    "error": (
                        "Knowledge Base search returned "
                        "NOT_FOUND after query rewriting."
                    ),
                    "next_worker": "END",
                    "trace": trace
                }

            # Use the second search result
            search_result = retry_result

        # =================================
        # BUILD KNOWLEDGE CONTEXT
        # =================================

        results = search_result.get("results", [])

        if not results:

            return {
                "rag_result": search_result,
                "error": (
                    "Knowledge Base returned FOUND "
                    "but no documents were provided."
                ),
                "next_worker": "END",
                "trace": trace
            }

        knowledge_context = "\n\n".join(
            (
                f"Source: {item.get('source', 'Unknown')}\n"
                f"Category: {item.get('category', 'General')}\n"
                f"Content:\n{item.get('content', '')}"
            )
            for item in results
        )

        if not knowledge_context.strip():

            return {
                "error": "Knowledge Context is empty.",
                "next_worker": "END",
                "trace": trace
            }

        # =================================
        # COMPLETED
        # =================================

        print(
            "\n[DATABASE SPECIALIST] "
            "Knowledge Base retrieval completed."
        )

        print(
            f"[DATABASE SPECIALIST] "
            f"Documents retrieved: {len(results)}"
        )

        if rewritten_query:
            print(
                "[DATABASE SPECIALIST] "
                "Query Rewriting was performed."
            )
        else:
            print(
                "[DATABASE SPECIALIST] "
                "Initial search succeeded."
            )

        return {
            "search_query": search_query,
            "rewritten_query": rewritten_query,
            "rag_result": search_result,
            "knowledge_context": knowledge_context,
            "next_worker": "sql_refactor",
            "trace": trace
        }

    except Exception as error:

        return {
            "error": str(error),
            "next_worker": "END",
            "trace": trace
        }
