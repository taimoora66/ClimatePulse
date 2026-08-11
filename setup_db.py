from pathlib import Path

from src.db import get_connection


def main():

    schema_path = (
        Path(__file__).parent
        / "database"
        / "schema.sql"
    )

    sql_text = schema_path.read_text(
        encoding="utf-8"
    )

    statements = [
        statement.strip()
        for statement in sql_text.split(";")
        if statement.strip()
    ]

    with get_connection() as conn:

        with conn.cursor() as cur:

            for statement in statements:
                cur.execute(statement)

    print(
        "ClimatePulse database initialized successfully."
    )


if __name__ == "__main__":
    main()