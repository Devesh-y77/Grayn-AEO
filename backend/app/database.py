"""
Grayn AEO — Database Client (Supabase & Postgres Direct Fallback)

Provides a singleton database client.
If SUPABASE_SERVICE_KEY is set in .env, initializes the real Supabase HTTP client.
Otherwise, falls back to a Direct Postgres Client wrapper that executes SQL queries
directly on DATABASE_URL using psycopg2 (with RealDictCursor). This allows seamless
local development and production database access using only the database password.
"""

import os
import logging
import psycopg2
import psycopg2.extras
from supabase import create_client, Client
from app.config import get_settings

logger = logging.getLogger("app.database")

# ── Direct Postgres Query Builder Wrapper ──────────────────

class QueryResult:
    def __init__(self, data):
        self.data = data


class DirectTableQuery:
    def __init__(self, conn, table_name):
        self.conn = conn
        self.table_name = table_name
        self.select_columns = "*"
        self.where_clauses = []
        self.where_args = []
        self.order_by = None
        self.limit_val = None
        self.is_single = False
        self.is_maybe_single = False
        self.insert_data = None
        self.upsert_data = None
        self.on_conflict = None
        self.update_data = None
        self.delete_flag = False

    def select(self, columns="*"):
        self.select_columns = columns
        return self

    def eq(self, column, value):
        self.where_clauses.append(f"{column} = %s")
        self.where_args.append(value)
        return self

    def in_(self, column, values):
        if not values:
            self.where_clauses.append("FALSE")
        else:
            placeholders = ", ".join(["%s"] * len(values))
            self.where_clauses.append(f"{column} IN ({placeholders})")
            self.where_args.extend(values)
        return self

    def order(self, column, desc=False):
        direction = "DESC" if desc else "ASC"
        self.order_by = f"{column} {direction}"
        return self

    def limit(self, count):
        self.limit_val = count
        return self

    def single(self):
        self.is_single = True
        return self

    def maybe_single(self):
        self.is_maybe_single = True
        return self

    def insert(self, data):
        self.insert_data = data
        return self

    def upsert(self, data, on_conflict=None):
        self.upsert_data = data
        self.on_conflict = on_conflict
        return self

    def update(self, data):
        self.update_data = data
        return self

    def delete(self):
        self.delete_flag = True
        return self

    def execute(self) -> QueryResult:
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            if self.insert_data is not None:
                # ── INSERT ───────────────────────────────────────
                if isinstance(self.insert_data, list):
                    if not self.insert_data:
                        return QueryResult([])
                    keys = list(self.insert_data[0].keys())
                    columns_str = ", ".join(keys)
                    placeholders = ", ".join(["%s"] * len(keys))
                    query_str = f"INSERT INTO {self.table_name} ({columns_str}) VALUES "
                    
                    value_clauses = []
                    args = []
                    for row in self.insert_data:
                        value_clauses.append(f"({placeholders})")
                        args.extend([row[k] for k in keys])
                    
                    query_str += ", ".join(value_clauses) + " RETURNING *;"
                    cur.execute(query_str, args)
                    rows = cur.fetchall()
                    return QueryResult([dict(r) for r in rows])
                else:
                    keys = list(self.insert_data.keys())
                    columns_str = ", ".join(keys)
                    placeholders = ", ".join(["%s"] * len(keys))
                    query_str = f"INSERT INTO {self.table_name} ({columns_str}) VALUES ({placeholders}) RETURNING *;"
                    args = [self.insert_data[k] for k in keys]
                    cur.execute(query_str, args)
                    row = cur.fetchone()
                    return QueryResult([dict(row)] if row else [])

            elif self.upsert_data is not None:
                # ── UPSERT ───────────────────────────────────────
                data = self.upsert_data
                if isinstance(data, list) and not data:
                    return QueryResult([])
                
                is_list = isinstance(data, list)
                sample = data[0] if is_list else data
                keys = list(sample.keys())
                columns_str = ", ".join(keys)
                placeholders = ", ".join(["%s"] * len(keys))
                
                query_str = f"INSERT INTO {self.table_name} ({columns_str}) VALUES "
                
                args = []
                if is_list:
                    value_clauses = []
                    for row in data:
                        value_clauses.append(f"({placeholders})")
                        args.extend([row[k] for k in keys])
                    query_str += ", ".join(value_clauses)
                else:
                    query_str += f"({placeholders})"
                    args = [sample[k] for k in keys]

                if self.on_conflict:
                    set_clauses = [f"{k} = EXCLUDED.{k}" for k in keys]
                    query_str += f" ON CONFLICT ({self.on_conflict}) DO UPDATE SET {', '.join(set_clauses)}"
                else:
                    query_str += " ON CONFLICT DO NOTHING"
                    
                query_str += " RETURNING *;"
                cur.execute(query_str, args)
                rows = cur.fetchall()
                return QueryResult([dict(r) for r in rows])

            elif self.update_data is not None:
                # ── UPDATE ───────────────────────────────────────
                set_clauses = []
                args = []
                for k, v in self.update_data.items():
                    set_clauses.append(f"{k} = %s")
                    args.append(v)
                
                query_str = f"UPDATE {self.table_name} SET {', '.join(set_clauses)}"
                
                if self.where_clauses:
                    query_str += f" WHERE {' AND '.join(self.where_clauses)}"
                    args.extend(self.where_args)
                
                query_str += " RETURNING *;"
                cur.execute(query_str, args)
                rows = cur.fetchall()
                return QueryResult([dict(r) for r in rows])

            elif self.delete_flag:
                # ── DELETE ───────────────────────────────────────
                query_str = f"DELETE FROM {self.table_name}"
                args = []
                if self.where_clauses:
                    query_str += f" WHERE {' AND '.join(self.where_clauses)}"
                    args.extend(self.where_args)
                query_str += " RETURNING *;"
                cur.execute(query_str, args)
                rows = cur.fetchall()
                return QueryResult([dict(r) for r in rows])

            else:
                # ── SELECT ───────────────────────────────────────
                # Special Join Translation for API keys verification:
                if self.table_name == "api_keys" and "workspaces(*)" in self.select_columns:
                    query_str = (
                        "SELECT api_keys.*, "
                        "workspaces.brand_name AS ws_brand_name, "
                        "workspaces.domain AS ws_domain, "
                        "workspaces.aliases AS ws_aliases, "
                        "workspaces.brand_context AS ws_brand_context, "
                        "workspaces.created_at AS ws_created_at "
                        "FROM api_keys "
                        "LEFT JOIN workspaces ON api_keys.workspace_id = workspaces.id"
                    )
                else:
                    query_str = f"SELECT {self.select_columns} FROM {self.table_name}"

                if self.where_clauses:
                    query_str += f" WHERE {' AND '.join(self.where_clauses)}"

                if self.order_by:
                    query_str += f" ORDER BY {self.order_by}"

                if self.limit_val:
                    query_str += f" LIMIT {self.limit_val}"

                cur.execute(query_str, self.where_args)
                rows = cur.fetchall()

                # Special Join Post-Processing
                data = []
                for r in rows:
                    row_dict = dict(r)
                    if "ws_brand_name" in row_dict:
                        # Reconstruct the workspace object structure expected by dependencies
                        row_dict["workspaces"] = {
                            "id": row_dict["workspace_id"],
                            "brand_name": row_dict.pop("ws_brand_name"),
                            "domain": row_dict.pop("ws_domain"),
                            "aliases": row_dict.pop("ws_aliases"),
                            "brand_context": row_dict.pop("ws_brand_context"),
                            "created_at": row_dict.pop("ws_created_at"),
                        }
                    data.append(row_dict)

                if self.is_single:
                    if not data:
                        raise ValueError("No rows returned for single()")
                    return QueryResult(data[0])
                elif self.is_maybe_single:
                    return QueryResult(data[0] if data else None)
                
                return QueryResult(data)

        finally:
            cur.close()


class DirectPostgresClient:
    """Mock/Wrapper client that interfaces like Supabase Python Client."""

    def __init__(self, database_url: str):
        self.database_url = database_url

    def table(self, table_name: str) -> DirectTableQuery:
        # Open connection on the fly per query request (avoids stale connections)
        conn = psycopg2.connect(self.database_url)
        conn.autocommit = True
        return DirectTableQuery(conn, table_name)


# ── Database Initialization ────────────────────────────────

_client = None


def get_supabase() -> Client:
    """
    Return the cached database client.
    
    If SUPABASE_SERVICE_KEY is configured, returns a Supabase HTTP Client.
    Otherwise, returns a DirectPostgresClient querying DB directly via psycopg2.
    """
    global _client
    if _client is None:
        settings = get_settings()
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
            logger.info("Initializing HTTP Supabase API Client")
            _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        elif settings.DATABASE_URL:
            logger.info("Initializing Direct Postgres DB Client (bypass PostgREST API)")
            _client = DirectPostgresClient(settings.DATABASE_URL)
        else:
            raise RuntimeError(
                "Neither (SUPABASE_URL + SUPABASE_SERVICE_KEY) nor DATABASE_URL is configured in .env!"
            )
    return _client
