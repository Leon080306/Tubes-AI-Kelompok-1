
import json
import uuid

from agents.supervisor import create_optimizer_graph
from tools.database_tools import explain_query


# =========================================
# CONFIGURATION
# =========================================

DEFAULT_SQL_QUERY = """
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


def print_execution_plan(title, result):

    print_section(title)

    if not result or not result.get("success"):

        print("Execution plan unavailable.")
        return

    for row in result.get("execution_plan", []):

        print("Table       :", row.get("table"))
        print("Access Type :", row.get("type"))
        print("Possible Key:", row.get("possible_keys"))
        print("Used Key    :", row.get("key"))
        print("Estimated Rows:", row.get("rows"))
        print("Extra       :", row.get("Extra"))


def print_react_trace(trace):

    print_section("REACT TRACE LOG")

    for index, event in enumerate(trace, start=1):

        print(f"\nSTEP {index}")

        print("Worker:", event.get("worker"))
        print("Thought:", event.get("thought"))
        print("Action:", event.get("action"))

        print("Observation:")

        observation = event.get("observation", {})

        # Avoid printing large document contents
        print_json(observation)


# =========================================
# MAIN APPLICATION
# =========================================

def main():

    print_section(
        "AUTOMATED DATABASE QUERY OPTIMIZER"
    )

    print("Powered by LangChain, LangGraph, and Ollama")
    print("Database: MySQL / MariaDB")

    # =====================================
    # GET USER INPUT
    # =====================================

    print("\nSample SQL Query:")
    print(DEFAULT_SQL_QUERY)

    custom_query = input(
        "\nEnter SQL Query (press ENTER to use sample): "
    ).strip()

    sql_query = custom_query or DEFAULT_SQL_QUERY

    # =====================================
    # INITIALIZE LANGGRAPH
    # =====================================

    print_section("INITIALIZING MULTI-AGENT SYSTEM")

    graph = create_optimizer_graph()

    thread_id = str(uuid.uuid4())

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    print("Thread ID:", thread_id)
    print("Graph initialized successfully.")

    # =====================================
    # INITIAL STATE
    # =====================================

    initial_state = {
        "sql_query": sql_query,
        "approval_status": "PENDING",
        "trace": []
    }

    # =====================================
    # RUN MULTI-AGENT WORKFLOW
    # =====================================

    print_section("RUNNING MULTI-AGENT WORKFLOW")

    graph.invoke(
        initial_state,
        config=config
    )

    # =====================================
    # INSPECT CHECKPOINT
    # =====================================

    snapshot = graph.get_state(config)

    workflow_state = snapshot.values

    print("\nWorkflow Status:",
          workflow_state.get("workflow_status"))

    print("Next Node:",
          snapshot.next)

    if workflow_state.get("error"):

        print("\nWorkflow Error:")
        print(workflow_state["error"])

        print_react_trace(
            workflow_state.get("trace", [])
        )

        return

    # =====================================
    # CHECK APPROVAL GATE
    # =====================================

    if "approval_gate" not in snapshot.next:

        print_section("WORKFLOW COMPLETED WITHOUT APPROVAL")

        status = workflow_state.get("workflow_status")

        if status == "NO_RECOMMENDATION":

            print(
                "No additional index recommendation is necessary."
            )

        else:

            print("Workflow did not reach DBA approval.")
            print("Status:", status)

        print_react_trace(
            workflow_state.get("trace", [])
        )

        return

    # =====================================
    # GET RECOMMENDATION
    # =====================================

    recommendation_result = workflow_state.get(
        "recommendation_result",
        {}
    )

    recommendation = recommendation_result.get(
        "recommendation",
        {}
    )

    validation = workflow_state.get(
        "recommendation_validation",
        {}
    )

    if validation.get("valid") is not True:

        print("\n[ERROR] Recommendation validation failed.")
        return

    proposed_sql = recommendation.get(
        "create_index_sql"
    )

    if not proposed_sql:

        print("\n[ERROR] CREATE INDEX SQL is unavailable.")
        return

    # =====================================
    # DISPLAY DBA APPROVAL REQUEST
    # =====================================

    print_section("HUMAN-IN-THE-LOOP: DBA APPROVAL")

    print("The AI system recommends the following index:")

    print("\nTable:")
    print(recommendation.get("table_name"))

    print("\nIndex Name:")
    print(recommendation.get("index_name"))

    print("\nColumns:")
    print(recommendation.get("columns"))

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

    print("\nProposed SQL:")
    print(proposed_sql)

    # =====================================
    # DBA DECISION
    # =====================================

    print("\n" + "-" * 70)

    print("1. APPROVE - Execute the recommended index.")
    print("2. REJECT  - Cancel the database modification.")

    while True:

        decision = input(
            "\nEnter your decision (1/2): "
        ).strip()

        if decision in ["1", "2"]:
            break

        print("Please enter 1 or 2.")

    approval_status = (
        "APPROVED"
        if decision == "1"
        else "REJECTED"
    )

    # =====================================
    # UPDATE CHECKPOINT
    # =====================================

    approval_trace = [{
        "worker": "Human-in-the-Loop",
        "thought": "The DBA reviewed the recommendation.",
        "action": "dba_approval",
        "parameters": {
            "decision": approval_status,
            "approved_sql": (
                proposed_sql
                if decision == "1"
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
                if decision == "1"
                else ""
            ),

            "approval_gate_reached": True,

            "trace": approval_trace
        },
        as_node="approval_gate"
    )

    print(
        "\n[CHECKPOINTER] Approval state successfully saved."
    )

    # =====================================
    # RESUME WORKFLOW
    # =====================================

    print_section("RESUMING LANGGRAPH WORKFLOW")

    final_result = graph.invoke(
        None,
        config=config
    )

    final_status = final_result.get(
        "workflow_status"
    )

    print("Final Workflow Status:", final_status)

    # =====================================
    # DISPLAY EXECUTION RESULT
    # =====================================

    print_section("DATABASE EXECUTION RESULT")

    print_json(
        final_result.get("execution_result")
    )

    print_section("INDEX VERIFICATION")

    print_json(
        final_result.get("verification_result")
    )

    # =====================================
    # COMPARE EXECUTION PLANS
    # =====================================

    if final_status == "COMPLETED":

        print_section("BEFORE VS AFTER OPTIMIZATION")

        before_plan = workflow_state.get(
            "execution_plan"
        )

        after_plan = explain_query.invoke({
            "sql_query": sql_query
        })

        print_execution_plan(
            "BEFORE OPTIMIZATION",
            before_plan
        )

        print_execution_plan(
            "AFTER OPTIMIZATION",
            after_plan
        )

    # =====================================
    # FINAL REACT TRACE
    # =====================================

    print_react_trace(
        final_result.get("trace", [])
    )

    # =====================================
    # FINAL STATUS
    # =====================================

    print_section("FINAL APPLICATION STATUS")

    if final_status == "COMPLETED":

        print("[SUCCESS] Index successfully created and verified.")

    elif final_status == "REJECTED":

        print("[CANCELLED] DBA rejected the recommendation.")
        print("[SAFE] No database changes were made.")

    else:

        print("[FAILED] Workflow did not complete.")

        if final_result.get("error"):
            print("Error:", final_result["error"])

    print("\nAPPLICATION FINISHED.")


# =========================================
# ENTRY POINT
# =========================================

if __name__ == "__main__":
    main()
