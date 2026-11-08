
import json

from agents.query_parser import query_parser_worker
from agents.database_specialist import database_specialist_worker
from agents.sql_refactor import sql_refactor_worker


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
# HELPER FUNCTIONS
# =========================================

def print_result(title, result):

    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

    printable = {
        key: value
        for key, value in result.items()
        if key != "trace"
    }

    print(json.dumps(
        printable,
        indent=4,
        ensure_ascii=False,
        default=str
    ))


def merge_state(state, update):

    for key, value in update.items():

        if key == "trace":
            state.setdefault("trace", []).extend(value)

        else:
            state[key] = value


# =========================================
# MAIN TEST
# =========================================

if __name__ == "__main__":

    # Initial shared state
    state = {
        "sql_query": SAMPLE_QUERY,
        "trace": []
    }

    # =====================================
    # WORKER 1: QUERY PARSER
    # =====================================

    print("\nSTARTING QUERY PARSER WORKER...")

    result = query_parser_worker(state)

    merge_state(state, result)

    print_result(
        "QUERY PARSER WORKER RESULT",
        result
    )

    if result.get("error"):
        print("\nWORKFLOW STOPPED:", result["error"])
        raise SystemExit(1)

    # =====================================
    # WORKER 2: DATABASE SPECIALIST
    # =====================================

    print("\nSTARTING DATABASE SPECIALIST WORKER...")

    result = database_specialist_worker(state)

    merge_state(state, result)

    print_result(
        "DATABASE SPECIALIST WORKER RESULT",
        result
    )

    if result.get("error"):
        print("\nWORKFLOW STOPPED:", result["error"])
        raise SystemExit(1)

    # =====================================
    # WORKER 3: SQL REFACTOR
    # =====================================

    print("\nSTARTING SQL REFACTOR WORKER...")

    result = sql_refactor_worker(state)

    merge_state(state, result)

    print_result(
        "SQL REFACTOR WORKER RESULT",
        result
    )

    if result.get("error"):
        print("\nWORKFLOW STOPPED:", result["error"])
        raise SystemExit(1)

    # =====================================
    # FINAL RESULT
    # =====================================

    print("\n" + "=" * 70)
    print("ALL WORKERS COMPLETED SUCCESSFULLY")
    print("=" * 70)

    recommendation = state.get(
        "recommendation_result", {}
    ).get("recommendation", {})

    validation = state.get(
        "recommendation_validation", {}
    )

    print("\nRECOMMENDED INDEX:")
    print(recommendation.get("create_index_sql"))

    print("\nVALIDATION STATUS:")
    print(validation.get("valid"))

    print("\nNEXT WORKER:")
    print(state.get("next_worker"))

    # =====================================
    # REACT TRACE LOG
    # =====================================

    print("\n" + "=" * 70)
    print("REACT TRACE LOG")
    print("=" * 70)

    for index, event in enumerate(state["trace"], start=1):

        print(f"\nSTEP {index}")
        print(f"Worker      : {event['worker']}")
        print(f"Thought     : {event['thought']}")
        print(f"Action      : {event['action']}")

        print("Observation :")

        print(json.dumps(
            event["observation"],
            indent=4,
            ensure_ascii=False,
            default=str
        ))

    print("\nWORKER TESTING COMPLETED.")
