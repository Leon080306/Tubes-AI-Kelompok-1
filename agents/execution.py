
from tools.execution_tools import (
    execute_create_index,
    verify_index_creation
)


# =========================================
# APPROVAL GATE NODE
# =========================================

def approval_gate_node(state: dict) -> dict:
    """
    Approval checkpoint placed immediately before
    the actual database execution node.

    Static interrupt_before will pause execution
    before this node.
    """

    print("\n[APPROVAL GATE] Waiting for DBA approval.")

    return {
        "approval_gate_reached": True
    }


# =========================================
# EXECUTE INDEX NODE
# =========================================

def execute_index_node(state: dict) -> dict:
    """
    Execute a previously validated and explicitly
    approved CREATE INDEX statement.

    This node is never exposed to the LLM.
    """

    trace = []

    def record(action, parameters, observation):

        trace.append({
            "worker": "Execute Index Node",
            "thought": (
                "Execute the approved database operation "
                "and verify its result."
            ),
            "action": action,
            "parameters": parameters,
            "observation": observation
        })

    try:

        # =================================
        # CHECK DBA APPROVAL
        # =================================

        approval_status = state.get(
            "approval_status",
            "PENDING"
        )

        if approval_status == "REJECTED":

            result = {
                "success": False,
                "status": "REJECTED",
                "message": (
                    "DBA rejected the index recommendation. "
                    "No database changes were made."
                )
            }

            record(
                "skip_database_execution",
                {
                    "approval_status": approval_status
                },
                result
            )

            return {
                "execution_result": result,
                "verification_result": None,
                "workflow_status": "REJECTED",
                "next_worker": "END",
                "trace": trace
            }

        if approval_status != "APPROVED":

            return {
                "error": (
                    "Database execution blocked. "
                    "Explicit DBA approval is required."
                ),
                "workflow_status": "BLOCKED",
                "next_worker": "END",
                "trace": trace
            }

        # =================================
        # RETRIEVE RECOMMENDATION
        # =================================

        recommendation_result = state.get(
            "recommendation_result",
            {}
        )

        recommendation = recommendation_result.get(
            "recommendation",
            {}
        )

        validation = state.get(
            "recommendation_validation",
            {}
        )

        proposed_sql = recommendation.get(
            "create_index_sql"
        )

        approved_sql = state.get(
            "approved_index_sql"
        )

        # =================================
        # VERIFY RECOMMENDATION
        # =================================

        if recommendation_result.get("status") != "RECOMMENDED":

            raise ValueError(
                "No valid index recommendation is available."
            )

        if validation.get("valid") is not True:

            raise ValueError(
                "Index recommendation has not passed validation."
            )

        # Exact-match approval check
        if not proposed_sql or approved_sql != proposed_sql:

            raise ValueError(
                "Approved SQL does not match the generated recommendation."
            )

        index_name = recommendation.get("index_name")

        table_name = recommendation.get("table_name")

        if not index_name or not table_name:

            raise ValueError(
                "Index name or table name is missing."
            )

        # =================================
        # ACTION 11: EXECUTE CREATE INDEX
        # =================================

        print("\n[EXECUTE INDEX] DBA approval confirmed.")

        execution_parameters = {
            "create_index_sql": approved_sql
        }

        execution_result = execute_create_index.invoke(
            execution_parameters
        )

        record(
            "execute_create_index",
            execution_parameters,
            execution_result
        )

        if not execution_result.get("success"):

            return {
                "execution_result": execution_result,
                "verification_result": None,
                "workflow_status": "EXECUTION_FAILED",
                "error": execution_result.get("error"),
                "next_worker": "END",
                "trace": trace
            }

        # =================================
        # ACTION 12: VERIFY INDEX CREATION
        # =================================

        verification_parameters = {
            "table_name": table_name,
            "index_name": index_name
        }

        verification_result = verify_index_creation.invoke(
            verification_parameters
        )

        record(
            "verify_index_creation",
            verification_parameters,
            verification_result
        )

        if verification_result.get("status") != "VERIFIED":

            return {
                "execution_result": execution_result,
                "verification_result": verification_result,
                "workflow_status": "EXECUTED_BUT_UNVERIFIED",
                "error": (
                    "Index creation succeeded, "
                    "but verification did not complete successfully."
                ),
                "next_worker": "END",
                "trace": trace
            }

        # =================================
        # COMPLETED
        # =================================

        print("\n[EXECUTE INDEX] Index successfully created.")

        return {
            "execution_result": execution_result,
            "verification_result": verification_result,
            "workflow_status": "COMPLETED",
            "next_worker": "END",
            "trace": trace
        }

    except Exception as error:

        return {
            "workflow_status": "EXECUTION_FAILED",
            "error": str(error),
            "next_worker": "END",
            "trace": trace
        }
