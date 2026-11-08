
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from config.settings import settings


def create_db_engine(username, password):
    database_url = URL.create(
        drivername="mysql+pymysql",
        username=username,
        password=password,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        query={"charset": "utf8mb4"}
    )

    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )


# Read-only database connection
read_engine = create_db_engine(
    settings.DB_READ_USER,
    settings.DB_READ_PASSWORD
)


# DBA database connection
dba_engine = create_db_engine(
    settings.DB_DBA_USER,
    settings.DB_DBA_PASSWORD
)



def test_connection(engine):
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT
                    VERSION() AS version,
                    DATABASE() AS database_name,
                    CURRENT_USER() AS db_user
            """)
        )

        return dict(result.mappings().one())


if __name__ == "__main__":
    print("Testing MySQL Connections...\n")

    try:
        reader = test_connection(read_engine)

        print("[SUCCESS] Read-only Connection")
        print(reader)

    except Exception as error:
        print("[FAILED] Read-only Connection")
        print(error)

    try:
        dba = test_connection(dba_engine)

        print("\n[SUCCESS] DBA Connection")
        print(dba)

    except Exception as error:
        print("[FAILED] DBA Connection")
        print(error)
