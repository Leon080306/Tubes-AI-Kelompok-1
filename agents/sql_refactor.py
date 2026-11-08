
from tools.optimization_tools import (
    generate_index_recommendation,
    validate_index_recommendation
)


# =========================================
# SQL REFACTOR WORKER
# =========================================

def sql_refactor_worker(state: dict) -> dict:
    """
    Generate and validate a database index recommendation.

    Handles:
    1. RECOMMENDED
    2. NO_RECOMMENDATION
    3. ERROR
    """

    trace = []

    def record(thought, action, parameters, observation):

        trace.append({
            "worker": "SQL Refactor Worker",
            "thought": thought,
            "action": action,
            "parameters": parameters,
            "observation": observation
        })

    try:

        # =================================
        # RETRIEVE SHARED STATE
        # =================================

        sql_query = state.get("sql_query", "")
        execution_plan = state.get("execution_plan", {})
        table_schema = state.get("table_schema", {})
        existing_indexes = state.get("existing_indexes", {})
        knowledge_context = state.get("knowledge_context", "")

        # =================================
        # CHECK REQUIRED INFORMATION
        # =================================

        required_data = {
            "SQL Query": sql_query,
            "Execution Plan": execution_plan,
            "Table Schema": table_schema,
            "Existing Indexes": existing_indexes,
            "Knowledge Context": knowledge_context
        }

        missing_data = [
            name
            for name, value in required_data.items()
            if not value
        ]

        if missing_data:

            return {
                "error": (
                    "Required information is missing: "
                    + ", ".join(missing_data)
                ),
                "workflow_status": "FAILED",
                "next_worker": "END",
                "trace": trace
            }

        # =================================
        # ACTION 1: GENERATE RECOMMENDATION
        # =================================

        parameters = {
            "sql_query": sql_query,
            "execution_plan": execution_plan,
            "table_schema": table_schema,
            "existing_indexes": existing_indexes,
            "knowledge_context": knowledge_context
        }

        recommendation_result = generate_index_recommendation.invoke(
            parameters
        )

        record(
            thought=(
                "Combine execution plan, table structure, "
                "existing indexes, and knowledge context "
                "to generate an index recommendation."
            ),
            action="generate_index_recommendation",
            parameters=parameters,
            observation=recommendation_result
        )

        status = recommendation_result.get("status")

        # =================================
        # CASE 1: NO RECOMMENDATION
        # =================================

        if status == "NO_RECOMMENDATION":

            print(
                "\n[SQL REFACTOR WORKER] "
                "No additional index is required."
            )

            return {
                "recommendation_result": recommendation_result,
                "recommendation_validation": None,
                "workflow_status": "NO_RECOMMENDATION",
                "next_worker": "supervisor",
                "trace": trace
            }

        # =================================
        # CASE 2: GENERATION ERROR
        # =================================

        if status != "RECOMMENDED":

            return {
                "recommendation_result": recommendation_result,
                "error": recommendation_result.get(
                    "message",
                    "Failed to generate index recommendation."
                ),
                "workflow_status": "FAILED",
                "next_worker": "END",
                "trace": trace
            }

        recommendation = recommendation_result.get(
            "recommendation", {}
        )

        create_index_sql = recommendation.get(
            "create_index_sql"
        )

        if not create_index_sql:

            return {
                "recommendation_result": recommendation_result,
                "error": "Generated CREATE INDEX SQL is empty.",
                "workflow_status": "FAILED",
                "next_worker": "END",
                "trace": trace
            }

        # =================================
        # ACTION 2: VALIDATE RECOMMENDATION
        # =================================

        validation_parameters = {
            "create_index_sql": create_index_sql,
            "table_schema": table_schema,
            "existing_indexes": existing_indexes
        }

        validation_result = validate_index_recommendation.invoke(
            validation_parameters
        )

        record(
            thought=(
                "Verify that the generated CREATE INDEX "
                "statement is valid and does not duplicate "
                "an existing index."
            ),
            action="validate_index_recommendation",
            parameters=validation_parameters,
            observation=validation_result
        )

        # =================================
        # CHECK VALIDATION RESULT
        # =================================

        if not validation_result.get("valid"):

            return {
                "recommendation_result": recommendation_result,
                "recommendation_validation": validation_result,
                "error": (
                    "Generated index recommendation "
                    "failed validation."
                ),
                "workflow_status": "FAILED",
                "next_worker": "END",
                "trace": trace
            }

        # =================================
        # PREPARE FOR DBA APPROVAL
        # =================================

        print(
            "\n[SQL REFACTOR WORKER] "
            "Recommendation generated and validated."
        )

        return {
            "recommendation_result": recommendation_result,
            "recommendation_validation": validation_result,
            "workflow_status": "READY_FOR_APPROVAL",
            "next_worker": "supervisor",
            "trace": trace
        }

    except Exception as error:

        return {
            "error": str(error),
            "workflow_status": "FAILED",
            "next_worker": "END",
            "trace": trace
        }
