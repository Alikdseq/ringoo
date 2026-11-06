#!/usr/bin/env python3
"""
Read-only диагностика ролей PostgreSQL для Ringoo.
Не выполняет GRANT/REVOKE. Не печатает пароли.

Usage (внутри web-контейнера или с DATABASE_URL):
  python scripts/check_postgres_privileges.py
"""

from __future__ import annotations

import os
import sys
import urllib.parse


def _connect():
    try:
        import psycopg2
    except ImportError:
        print("FAIL: psycopg2 not installed", file=sys.stderr)
        return None
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return psycopg2.connect(url)
    host = os.getenv("DB_HOST", "db")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "ringoo")
    user = os.getenv("DB_USER", "")
    password = os.getenv("DB_PASSWORD", "")
    if not user:
        print("FAIL: set DATABASE_URL or DB_USER", file=sys.stderr)
        return None
    return psycopg2.connect(
        host=host, port=port, dbname=name, user=user, password=password
    )


def main() -> int:
    conn = _connect()
    if conn is None:
        return 2
    weak = {"postgres", "root", "admin", "superuser"}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user, session_user")
            current_user, session_user = cur.fetchone()
            print(f"current_user={current_user} session_user={session_user}")
            if current_user.lower() in weak:
                print("WARN: connected as weak/default role name")
            cur.execute(
                """
                SELECT r.rolname, r.rolsuper, r.rolcreatedb, r.rolcreaterole, r.rolcanlogin
                FROM pg_roles r
                WHERE r.rolname = current_user
                """
            )
            row = cur.fetchone()
            if not row:
                print("FAIL: role not found")
                return 1
            name, superuser, createdb, createrole, canlogin = row
            print(
                f"role={name} superuser={superuser} createdb={createdb} "
                f"createrole={createrole} canlogin={canlogin}"
            )
            ok = not superuser and not createdb and not createrole and canlogin
            if ok:
                print("OK: role flags look like least-privilege app user")
                return 0
            print("FAIL: role has elevated flags")
            return 1
    finally:
        conn.close()


if __name__ == "__main__":
    # Avoid accidental password echo via argv
    if any("password" in a.lower() for a in sys.argv[1:]):
        print("Do not pass passwords on the command line.", file=sys.stderr)
        sys.exit(2)
    raise SystemExit(main())
