
from typing import Literal

from langgraph.graph import (
    StateGraph,
    START,
    END
)

from langgraph.checkpoint.memory import MemorySaver

from agents.state import OptimizerState

from agents.query_parser import query_parser_worker
from agents.database_specialist import database_specialist_worker
from agents.sql_refactor import sql_refactor_worker

from agents.execution import (
    approval_gate_node,
    execute_index_node
)


# =========================================
# SUPERVISOR NODE
# =========================================

def supervisor_node(state: OptimizerState) -> dict:
    """
    Coordinate workers using deterministic
    conditional routing.
    """

    error = state.get("error")

    recommendation = state.get(
        "recommendation_result", {}
    )

    recommendation_status = recommendation.get("status")

    validation = state.get(
        "recommendation_validation", {}
    )

    def create_trace(thought, next_worker, status):

        return [{
            "worker": "Supervisor Agent",
            "thought": thought,
            "action": "conditional_routing",
            "parameters": {
                "next_worker": next_worker
            },
            "observation": {
                "workflow_status": status
            }
        }]

    # CASE 1: NO RECOMMENDATION

    if recommendation_status == "NO_RECOMMENDATION":

        status = "NO_RECOMMENDATION"

        return {
            "next_worker": "END",
            "current_worker": "supervisor",
            "workflow_status": status,
            "trace": create_trace(
                "No additional index is justified. Stop the workflow without modifying the database.",
                "END",
                status
            )
    }


# CASE 2: ERROR HANDLING

    if error:

        status = "FAILED"

        return {
            "next_worker": "END",
            "current_worker": "supervisor",
            "workflow_status": status,
            "trace": create_trace(
                "A worker reported an error. Stop the workflow.",
                "END",
                status
            )
        }

    # =====================================
    # CASE 3: QUERY PARSER
    # =====================================

    if not state.get("sql_validation"):

        next_worker = "query_parser"
        status = "QUERY_ANALYSIS"

        thought = (
            "SQL has not been analyzed. "
            "Assign Query Parser Worker."
        )

    # =====================================
    # CASE 4: DATABASE SPECIALIST
    # =====================================

    elif not state.get("knowledge_context"):

        if not state.get("parsed_query"):

            return {
                "error": "Parsed SQL information is missing.",
                "next_worker": "END",
                "workflow_status": "FAILED",
                "trace": create_trace(
                    "Parsed SQL information is missing.",
                    "END",
                    "FAILED"
                )
            }

        next_worker = "database_specialist"
        status = "KNOWLEDGE_RETRIEVAL"

        thought = (
            "Database analysis is complete. "
            "Retrieve relevant SQL optimization guidelines."
        )

    # =====================================
    # CASE 5: SQL REFACTOR
    # =====================================

    elif not recommendation:

        next_worker = "sql_refactor"
        status = "SQL_OPTIMIZATION"

        thought = (
            "Knowledge Context is available. "
            "Generate and validate an index recommendation."
        )

    # =====================================
    # CASE 6: DBA APPROVAL
    # =====================================

    elif (
        recommendation_status == "RECOMMENDED"
        and validation.get("valid") is True
    ):

        next_worker = "approval_gate"
        status = "READY_FOR_APPROVAL"

        thought = (
            "The index recommendation is valid. "
            "Pause the workflow before database execution "
            "and request DBA approval."
        )

    # =====================================
    # CASE 7: INVALID RESULT
    # =====================================

    else:

        return {
            "error": "Recommendation is incomplete or invalid.",
            "next_worker": "END",
            "workflow_status": "FAILED",
            "trace": create_trace(
                "The recommendation did not pass validation.",
                "END",
                "FAILED"
            )
        }

    # =====================================
    # RETURN ROUTING DECISION
    # =====================================

    print(
        f"\n[SUPERVISOR] Next Worker: {next_worker}"
    )

    return {
        "next_worker": next_worker,
        "current_worker": "supervisor",
        "workflow_status": status,
        "trace": create_trace(
            thought,
            next_worker,
            status
        )
    }


# =========================================
# CONDITIONAL ROUTING
# =========================================

def route_next_worker(
    state: OptimizerState
) -> Literal[
    "query_parser",
    "database_specialist",
    "sql_refactor",
    "approval_gate",
    "END"
]:

    return state.get("next_worker", "END")


# =========================================
# BUILD LANGGRAPH STATEGRAPH
# =========================================

def create_optimizer_graph(
    checkpointer=None
):

    builder = StateGraph(OptimizerState)

    # -------------------------------------
    # REGISTER NODES
    # -------------------------------------

    builder.add_node(
        "supervisor",
        supervisor_node
    )

    builder.add_node(
        "query_parser",
        query_parser_worker
    )

    builder.add_node(
        "database_specialist",
        database_specialist_worker
    )

    builder.add_node(
        "sql_refactor",
        sql_refactor_worker
    )

    builder.add_node(
        "approval_gate",
        approval_gate_node
    )

    builder.add_node(
        "execute_index",
        execute_index_node
    )

    # -------------------------------------
    # ENTRY POINT
    # -------------------------------------

    builder.add_edge(
        START,
        "supervisor"
    )

    # -------------------------------------
    # SUPERVISOR CONDITIONAL ROUTING
    # -------------------------------------

    builder.add_conditional_edges(
        "supervisor",
        route_next_worker,
        {
            "query_parser": "query_parser",
            "database_specialist": "database_specialist",
            "sql_refactor": "sql_refactor",
            "approval_gate": "approval_gate",
            "END": END
        }
    )

    # -------------------------------------
    # WORKER -> SUPERVISOR
    # -------------------------------------

    builder.add_edge(
        "query_parser",
        "supervisor"
    )

    builder.add_edge(
        "database_specialist",
        "supervisor"
    )

    builder.add_edge(
        "sql_refactor",
        "supervisor"
    )

    # -------------------------------------
    # APPROVAL -> EXECUTION
    # -------------------------------------

    builder.add_edge(
        "approval_gate",
        "execute_index"
    )

    builder.add_edge(
        "execute_index",
        END
    )

    # -------------------------------------
    # CHECKPOINTER
    # -------------------------------------

    if checkpointer is None:
        checkpointer = MemorySaver()

    # -------------------------------------
    # COMPILE GRAPH
    # -------------------------------------

    graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["approval_gate"],
        name="Automated Database Query Optimizer"
    )

    return graph
