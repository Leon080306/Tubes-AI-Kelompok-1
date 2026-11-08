
import json
import uuid

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
# HELPER FUNCTIONS
# =========================================

def print_section(title):

    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_json(data):

    print(json.dumps(
        data,
        indent=4,
        ensure_ascii=False,
        default=str
    ))


# =========================================
# MAIN
# =========================================

if __name__ == "__main__":

    print_section(
        "AUTOMATED DATABASE QUERY OPTIMIZER"
    )

    # =====================================
    # INITIALIZE GRAPH
    # =====================================

    graph = create_optimizer_graph()

    # Each run gets a unique thread ID
    thread_id = str(uuid.uuid4())

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    print("\nThread ID:", thread_id)

    # =====================================
    # INITIAL STATE
    # =====================================

    initial_state = {
        "sql_query": SAMPLE_QUERY,
        "approval_status": "PENDING",
        "trace": []
    }

    # =====================================
    # STEP 1: RUN MULTI-AGENT WORKFLOW
    # =====================================

    print_section(
        "STEP 1: RUNNING MULTI-AGENT WORKFLOW"
    )

    graph.invoke(
        initial_state,
        config=config
    )

    print("\n[MAIN] Workflow execution paused.")

    # =====================================
    # STEP 2: RETRIEVE CHECKPOINT
    # =====================================

    snapshot = graph.get_state(config)

    print_section(
        "STEP 2: CHECKPOINT INFORMATION"
    )

    print("Next Node:", snapshot.next)

    print("Workflow Status:",
          snapshot.values.get("workflow_status"))

    print("Approval Status:",
          snapshot.values.get("approval_status"))

    # Confirm that the workflow is actually paused
    if "approval_gate" not in snapshot.next:

        print("\n[MAIN] Approval Gate was not reached.")

        if snapshot.values.get("error"):
            print("Error:", snapshot.values["error"])

        print("Workflow Status:",
              snapshot.values.get("workflow_status"))

        raise SystemExit(1)

    # =====================================
    # STEP 3: DISPLAY RECOMMENDATION
    # =====================================

    recommendation_result = snapshot.values.get(
        "recommendation_result",
        {}
    )

    recommendation = recommendation_result.get(
        "recommendation",
        {}
    )

    validation = snapshot.values.get(
        "recommendation_validation",
        {}
    )

    if validation.get("valid") is not True:

        print("\n[MAIN] Recommendation validation failed.")

        raise SystemExit(1)

    proposed_sql = recommendation.get(
        "create_index_sql"
    )

    if not proposed_sql:

        print("\n[MAIN] No CREATE INDEX statement found.")

        raise SystemExit(1)

    print_section(
        "STEP 3: DBA APPROVAL REQUEST"
    )

    print("Table:",
          recommendation.get("table_name"))

    print("Index Name:",
          recommendation.get("index_name"))

    print("Columns:",
          recommendation.get("columns"))

    print("\nReason:")

    print(recommendation.get("reason"))

    print("\nExpected Benefits:")

    print_json(
        recommendation.get("expected_benefits", [])
    )

    print("\nRisks:")

    print_json(
        recommendation.get("risks", [])
    )

    print("\nCREATE INDEX SQL:")

    print(proposed_sql)

    # =====================================
    # STEP 4: DBA DECISION
    # =====================================

    print_section(
        "STEP 4: HUMAN APPROVAL"
    )

    while True:

        decision = input(
            "\nDBA Decision (APPROVE / REJECT): "
        ).strip().upper()

        if decision in ["APPROVE", "REJECT"]:
            break

        print("Invalid decision. Please enter APPROVE or REJECT.")

    # =====================================
    # STEP 5: UPDATE CHECKPOINT STATE
    # =====================================

    approval_status = (
        "APPROVED"
        if decision == "APPROVE"
        else "REJECTED"
    )

    approval_trace = [{
        "worker": "Human-in-the-Loop",
        "thought": (
            "The DBA reviewed the index recommendation "
            "and provided an approval decision."
        ),
        "action": "dba_approval",
        "parameters": {
            "decision": decision,
            "approved_sql": (
                proposed_sql
                if decision == "APPROVE"
                else None
            )
        },
        "observation": {
            "approval_status": approval_status
        }
    }]

    graph.update_state(
        config,
        {
            "approval_status": approval_status,

            "approved_index_sql": (
                proposed_sql
                if decision == "APPROVE"
                else ""
            ),

            "approval_gate_reached": True,

            "trace": approval_trace
        },
        as_node="approval_gate"
    )

    print(
        f"\n[MAIN] Approval state saved: {approval_status}"
    )

    # =====================================
    # STEP 6: RESUME WORKFLOW
    # =====================================

    print_section(
        "STEP 5: RESUMING WORKFLOW"
    )

    final_result = graph.invoke(
        None,
        config=config
    )

    # =====================================
    # STEP 7: FINAL RESULT
    # =====================================

    print_section(
        "FINAL WORKFLOW RESULT"
    )

    print("Workflow Status:",
          final_result.get("workflow_status"))

    print("Approval Status:",
          final_result.get("approval_status"))

    execution_result = final_result.get(
        "execution_result"
    )

    verification_result = final_result.get(
        "verification_result"
    )

    print("\nEXECUTION RESULT:")

    print_json(execution_result)

    print("\nVERIFICATION RESULT:")

    print_json(verification_result)

    # =====================================
    # STEP 8: REACT TRACE LOG
    # =====================================

    print_section(
        "REACT TRACE LOG"
    )

    for index, event in enumerate(
        final_result.get("trace", []),
        start=1
    ):

        print(f"\nSTEP {index}")

        print("Worker:",
              event.get("worker"))

        print("Thought:",
              event.get("thought"))

        print("Action:",
              event.get("action"))

        print("Observation:")

        observation = event.get("observation")

        print_json(observation)

    # =====================================
    # FINAL STATUS
    # =====================================

    print_section(
        "FINAL STATUS"
    )

    status = final_result.get("workflow_status")

    if status == "COMPLETED":

        print("[SUCCESS] Index created and verified.")

    elif status == "REJECTED":

        print("[CANCELLED] DBA rejected the recommendation.")

        print("[SAFE] No database changes were made.")

    else:

        print("[FAILED] Workflow did not complete successfully.")

        if final_result.get("error"):
            print("Error:", final_result["error"])

    print("\nHUMAN-IN-THE-LOOP TESTING COMPLETED.")
