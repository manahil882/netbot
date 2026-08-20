"""Apply pending Supabase schema migrations.

Requires DATABASE_URL or SUPABASE_DB_PASSWORD in backend/.env

Get the database password from:
Supabase Dashboard → Project Settings → Database → Database password
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv(".env")

MIGRATIONS = [
    """
    ALTER TABLE users ADD COLUMN IF NOT EXISTS face_embedding JSONB;
    """,
]


def build_database_url() -> str:
    if url := os.getenv("DATABASE_URL"):
        return url.strip()

    password = os.getenv("SUPABASE_DB_PASSWORD")
    if not password:
        raise SystemExit(
            "Missing DATABASE_URL or SUPABASE_DB_PASSWORD in backend/.env\n"
            "Find the password in Supabase → Settings → Database → Database password"
        )

    project_ref = os.getenv("SUPABASE_PROJECT_REF", "kbwzvizryaiwkfktfvpv")
    host = os.getenv("SUPABASE_DB_HOST", f"db.{project_ref}.supabase.co")
    return f"postgresql://postgres:{password}@{host}:5432/postgres"


def main() -> None:
    try:
        import psycopg2
    except ImportError:
        raise SystemExit("Install psycopg2-binary: pip install psycopg2-binary")

    database_url = build_database_url()
    print("Connecting to Supabase Postgres…")

    with psycopg2.connect(database_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            for sql in MIGRATIONS:
                print(f"Running: {sql.strip().splitlines()[0]}…")
                cur.execute(sql)

            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'face_embedding';
                """
            )
            row = cur.fetchone()
            if row:
                print("Verified: users.face_embedding exists.")
            else:
                print("ERROR: face_embedding column still missing.")
                sys.exit(1)

    print("Migration complete.")


if __name__ == "__main__":
    main()
