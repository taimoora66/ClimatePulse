from src.db import get_connection


def main():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    current_database() AS database_name,
                    current_user AS user_name,
                    version() AS postgres_version;
            """)

            result = cur.fetchone()

    print()
    print("PostgreSQL connection successful!")
    print("Database:", result["database_name"])
    print("User:", result["user_name"])
    print("Version:", result["postgres_version"])


if __name__ == "__main__":
    main()