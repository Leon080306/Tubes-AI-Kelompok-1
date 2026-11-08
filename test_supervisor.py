
import json

from agents.supervisor import create_optimizer_graph


# =========================================
# SAMPLE SQL QUERY
# =========================================

SAMPLE_QUERY = """
SELECT *
FROM orders
WHERE customer_id = 105
ORDER BY created_at DESC
LIMIT 10;
"""


# =========================================
# HELPER: PRINT RESULTS
# =========================================

def print_section(title):

    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


# =========================================
# MAIN
# =========================================

if __name__ == "__main__":

    print_section(
        "AUTOMATED DATABASE QUERY OPTIMIZER"
    )

    # Build LangGraph
    graph = create_optimizer_graph()

    print("\n[MAIN] LangGraph initialized successfully.")

    # Initial state
    initial_state = {
        "sql_query": SAMPLE_QUERY,
        "trace": []
    }

    # -------------------------------------
    # RUN STATEGRAPH
    # -------------------------------------

    print("\n[MAIN] Starting Multi-Agent Workflow...")

    result = graph.invoke(
        initial_state,
        config={
            "recursion_limit": 20
        }
    )

    # -------------------------------------
    # WORKFLOW RESULT
    # -------------------------------------

    print_section("WORKFLOW RESULT")

    print(
        "Workflow Status:",
        result.get("workflow_status")
    )

    print(
        "Current Worker:",
        result.get("current_worker")
    )

    print(
        "Next Worker:",
        result.get("next_worker")
    )

    if result.get("error"):

        print(
            "\nWorkflow Error:",
            result["error"]
        )

    # -------------------------------------
    # SQL RECOMMENDATION
    # -------------------------------------

    recommendation_result = result.get(
        "recommendation_result", {}
    )

    recommendation = recommendation_result.get(
        "recommendation", {}
    )

    validation = result.get(
        "recommendation_validation", {}
    )

    print_section("INDEX RECOMMENDATION")

    print(
        "Recommendation Status:",
        recommendation_result.get("status")
    )

    if recommendation:

        print(
            "Index Name:",
            recommendation.get("index_name")
        )

        print(
            "Table:",
            recommendation.get("table_name")
        )

        print(
            "Columns:",
            recommendation.get("columns")
        )

        print(
            "\nCREATE INDEX SQL:"
        )

        print(
            recommendation.get("create_index_sql")
        )

    print(
        "\nValidation Status:",
        validation.get("valid")
    )

    # -------------------------------------
    # REACT TRACE LOG
    # -------------------------------------

    print_section("REACT TRACE LOG")

    traces = result.get("trace", [])

    for index, event in enumerate(traces, start=1):

        print(f"\nSTEP {index}")

        print(
            "Worker:",
            event.get("worker")
        )

        print(
            "Thought:",
            event.get("thought")
        )

        print(
            "Action:",
            event.get("action")
        )

        print(
            "Parameters:",
            json.dumps(
                event.get("parameters"),
                ensure_ascii=False,
                default=str
            )
        )

        observation = event.get("observation")

        if isinstance(observation, dict):

            observation_summary = {
                key: value
                for key, value in observation.items()
                if key not in ["content"]
            }

            print(
                "Observation:",
                json.dumps(
                    observation_summary,
                    ensure_ascii=False,
                    default=str
                )
            )

    # -------------------------------------
    # FINAL STATUS
    # -------------------------------------

    print_section("FINAL STATUS")

    if result.get("workflow_status") == "READY_FOR_APPROVAL":

        print(
            "[SUCCESS] All workers completed successfully."
        )

        print(
            "[PENDING] Waiting for DBA approval."
        )

    elif result.get("workflow_status") == "NO_RECOMMENDATION":

        print(
            "[INFO] No index recommendation was necessary."
        )

    else:

        print(
            "[FAILED] Workflow did not complete successfully."
        )

    print("\nMulti-Agent Testing Completed.")
