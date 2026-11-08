
import json

from tools.execution_tools import (
    execute_create_index,
    verify_index_creation
)


# =========================================
# HELPER: PRINT RESULT
# =========================================

def print_result(title, result):

    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    print(json.dumps(
        result,
        indent=4,
        ensure_ascii=False,
        default=str
    ))


# =========================================
# TEST 1: VERIFY EXISTING PRIMARY INDEX
# =========================================

def test_existing_index():

    result = verify_index_creation.invoke({
        "table_name": "orders",
        "index_name": "PRIMARY"
    })

    print_result(
        "TEST 1: VERIFY EXISTING PRIMARY INDEX",
        result
    )

    return result


# =========================================
# TEST 2: VERIFY NON-EXISTING INDEX
# =========================================

def test_missing_index():

    result = verify_index_creation.invoke({
        "table_name": "orders",
        "index_name": "idx_orders_customer_created"
    })

    print_result(
        "TEST 2: VERIFY NON-EXISTING INDEX",
        result
    )

    return result


# =========================================
# TEST 3: REJECT UNSAFE SQL
# =========================================

def test_unsafe_sql():

    result = execute_create_index.invoke({
        "create_index_sql": """
            DROP TABLE orders
        """
    })

    print_result(
        "TEST 3: REJECT UNSAFE SQL",
        result
    )

    return result


# =========================================
# TEST 4: REJECT INVALID COLUMN
# =========================================

def test_invalid_column():

    result = execute_create_index.invoke({
        "create_index_sql": """
            CREATE INDEX idx_invalid
            ON orders (unknown_column)
        """
    })

    print_result(
        "TEST 4: REJECT INVALID COLUMN",
        result
    )

    return result


# =========================================
# MAIN
# =========================================

if __name__ == "__main__":

    existing = test_existing_index()

    missing = test_missing_index()

    unsafe = test_unsafe_sql()

    invalid = test_invalid_column()

    print("\n" + "=" * 60)
    print("EXECUTION TOOLS TEST SUMMARY")
    print("=" * 60)

    print(
        "Existing Index Verified:",
        existing.get("status") == "VERIFIED"
    )

    print(
        "Missing Index Detected:",
        missing.get("status") == "NOT_FOUND"
    )

    print(
        "Unsafe SQL Rejected:",
        unsafe.get("success") is False
    )

    print(
        "Invalid Column Rejected:",
        invalid.get("success") is False
    )

    print("\nTESTING COMPLETED.")
