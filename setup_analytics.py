from pathlib import Path

from src.db import get_connection


def main():

    sql_path = Path("database/analytics.sql")

    sql = sql_path.read_text(
        encoding="utf-8"
    )

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(sql)

    print("ClimatePulse analytics views created successfully!")


if __name__ == "__main__":
    main()