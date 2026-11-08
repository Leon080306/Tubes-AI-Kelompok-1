
from typing import TypedDict, Annotated, Any
import operator


# =========================================
# OPTIMIZER SHARED STATE
# =========================================

class OptimizerState(TypedDict, total=False):

    # =====================================
    # USER INPUT
    # =====================================

    sql_query: str

    # =====================================
    # QUERY PARSER WORKER
    # =====================================

    sql_validation: dict
    parsed_query: dict

    table_analyses: dict
    table_schema: dict
    existing_indexes: dict
    table_statistics: dict

    execution_plan: dict

    # =====================================
    # DATABASE SPECIALIST WORKER
    # =====================================

    search_query: str
    rag_result: dict
    rewritten_query: str
    knowledge_context: str

    # =====================================
    # SQL REFACTOR WORKER
    # =====================================

    recommendation_result: dict
    recommendation_validation: dict

    # =====================================
    # SUPERVISOR
    # =====================================

    next_worker: str
    current_worker: str
    workflow_status: str
    error: str

    # =====================================
    # HUMAN-IN-THE-LOOP
    # =====================================

    approval_status: str
    approved_index_sql: str
    approval_gate_reached: bool

    # =====================================
    # EXECUTION RESULT
    # =====================================

    execution_result: dict
    verification_result: dict

    # =====================================
    # REACT TRACE LOG
    # =====================================

    trace: Annotated[
        list[dict[str, Any]],
        operator.add
    ]
