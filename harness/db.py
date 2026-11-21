"""Local PostgreSQL 16 (pgserver) and per-configuration database builds.

A configuration is an ordered list of SQL texts: shim -> app schema (possibly mutated) -> [improvement] -> fixtures.
Every configuration gets a brand-new database in a brand-new throw-away cluster directory, so runs never share state.
"""
from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path

import pgserver
import psycopg

ROOT = Path(__file__).resolve().parent.parent
SHIM = ROOT / 'harness' / 'supabase_shim.sql'
FIXTURES = ROOT / 'harness' / 'fixtures.sql'
SCHEMA = ROOT / 'target' / 'app-under-test' / 'supabase' / 'schema.sql'
IMPROVEMENT_DIR = ROOT / 'improvement'


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


class Cluster:
    """One throw-away PostgreSQL cluster for a whole study invocation."""

    def __init__(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix='a5-pg-'))
        self.server = pgserver.get_server(self.dir, cleanup_mode='stop')
        self.base_uri = self.server.get_uri()
        with psycopg.connect(self.base_uri, autocommit=True) as c:
            for role in ('anon', 'authenticated', 'service_role'):
                c.execute(f"do $$ begin if not exists (select 1 from pg_roles where rolname = '{role}') "
                          f"then create role {role} nologin; end if; end $$;")
            self.server_version = c.execute('show server_version').fetchone()[0]

    def uri(self, dbname: str) -> str:
        return self.base_uri.rsplit('/', 1)[0] + '/' + dbname

    def build(self, dbname: str, sql_texts: list[tuple[str, str]]) -> str:
        """Create database `dbname` and run each (label, sql) in order. Returns its URI."""
        with psycopg.connect(self.base_uri, autocommit=True) as c:
            c.execute(f'drop database if exists {dbname}')
            c.execute(f'create database {dbname} template template0')
        uri = self.uri(dbname)
        with psycopg.connect(uri, autocommit=True) as c:
            for label, sql in sql_texts:
                try:
                    c.execute(sql)
                except Exception as exc:  # surfaced to the caller with the failing step
                    raise RuntimeError(f'build {dbname}: step {label!r} failed: {exc}') from exc
        return uri

    def close(self) -> None:
        try:
            self.server.cleanup()
        finally:
            shutil.rmtree(self.dir, ignore_errors=True)


def improvement_files() -> list[Path]:
    return sorted(IMPROVEMENT_DIR.glob('*.sql'))


def config_sql(config: str, schema_text: str | None = None) -> list[tuple[str, str]]:
    """SQL steps for 'before' (frozen app) or 'after' (frozen app + improvement migrations)."""
    steps = [('shim', read(SHIM)), ('schema', schema_text if schema_text is not None else read(SCHEMA))]
    if config == 'after':
        files = improvement_files()
        if not files:
            raise RuntimeError("config 'after' requested but improvement/ has no .sql file")
        steps += [(f'improvement:{p.name}', read(p)) for p in files]
    elif config != 'before':
        raise ValueError(config)
    steps.append(('fixtures', read(FIXTURES)))
    return steps
