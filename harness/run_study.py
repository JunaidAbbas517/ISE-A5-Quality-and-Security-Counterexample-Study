"""Run the frozen A5 procedure and write raw results.

  python harness/run_study.py --config before --runs 3     # baseline (frozen app)
  python harness/run_study.py --config after  --runs 3     # frozen app + improvement/*.sql
  python harness/run_study.py --mutants                    # oracle check: mutation set on the frozen app

Each invocation starts a fresh throw-away PostgreSQL cluster, builds the configuration from scratch and writes
results/raw/<UTC stamp>-<name>.json (machine-readable) and .txt (human-readable). Nothing is overwritten.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cases as case_mod  # noqa: E402
import db  # noqa: E402
import mutants as mutant_mod  # noqa: E402

ROOT = db.ROOT
RAW = ROOT / 'results' / 'raw'
UNCHANGED = re.compile(r'UNCHANGED\((\w+)\)')


def git_state() -> dict:
    def git(*args):
        try:
            return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception:
            return ''
    return {'commit': git('rev-parse', 'HEAD') or 'none', 'dirty': bool(git('status', '--porcelain'))}


def environment(cluster: db.Cluster, config: str) -> dict:
    inputs = {
        'schema.sql': db.sha256_file(db.SCHEMA),
        'supabase_shim.sql': db.sha256_file(db.SHIM),
        'fixtures.sql': db.sha256_file(db.FIXTURES),
        'cases.py': db.sha256_file(Path(case_mod.__file__)),
        'mutants.py': db.sha256_file(Path(mutant_mod.__file__)),
        'run_study.py': db.sha256_file(Path(__file__)),
    }
    if config == 'after':
        inputs.update({f'improvement/{p.name}': db.sha256_file(p) for p in db.improvement_files()})
    return {
        'utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'python': sys.version.split()[0],
        'psycopg': psycopg.__version__,
        'postgres': cluster.server_version,
        'os': platform.platform(),
        'git': git_state(),
        'case_set': 'a5-cases-v1', 'case_count': len(case_mod.CASES),
        'fixture_set': 'a5-fixtures-v1',
        'input_sha256': inputs,
    }


def expand(text: str, ids: dict) -> str:
    return text.format(**ids)


def check_sql(check: str) -> str:
    def repl(m):
        t = m.group(1)
        return (f"(not exists ((table public.{t} except all table a5_snap_{t}) "
                f"union all (table a5_snap_{t} except all table public.{t})))")
    return 'select ' + UNCHANGED.sub(repl, check)


def run_case(conn: psycopg.Connection, case: dict, ids: dict) -> dict:
    res = {k: case[k] for k in ('id', 'claim', 'kind', 'actor', 'expect')}
    error = None
    rowcount = None
    try:
        with conn.cursor() as cur:
            for t in case_mod.SNAPSHOT_TABLES:
                cur.execute(f'create temp table a5_snap_{t} on commit drop as table public.{t}')
            if case.get('pre'):
                cur.execute(expand(case['pre'], ids))
            cur.execute('savepoint act')
            actor = case['actor']
            if actor == 'anon':
                cur.execute("select set_config('request.jwt.claim.sub', '', true)")
                cur.execute('set local role anon')
            elif actor != 'auth':
                cur.execute("select set_config('request.jwt.claim.sub', %s, true)", (case_mod.ACTORS[actor],))
                cur.execute('set local role authenticated')
            try:
                cur.execute(expand(case['sql'], ids))
                rowcount = cur.rowcount
                if cur.description is not None:
                    cur.fetchall()
                cur.execute('release savepoint act')
            except psycopg.Error as exc:
                error = {'sqlstate': exc.sqlstate, 'message': str(exc).strip().splitlines()[0]}
                cur.execute('rollback to savepoint act')
            cur.execute('reset role')
            check_ok = True
            if case.get('check'):
                check_ok = bool(cur.execute(check_sql(expand(case['check'], ids))).fetchone()[0])
    finally:
        conn.rollback()

    expect = case['expect']
    if expect == 'error':
        action_ok = error is not None
    elif expect == 'none':
        action_ok = error is not None or rowcount == 0
    else:  # ok
        action_ok = error is None and (rowcount or 0) >= 1
    verdict = 'PASS' if action_ok and check_ok else 'FAIL'
    res.update(error=error, rowcount=rowcount, state_check=check_ok, verdict=verdict,
               counterexample=(verdict == 'FAIL' and case['kind'] != 'control'))
    return res


def run_all(uri: str) -> list[dict]:
    with psycopg.connect(uri, options='-c TimeZone=UTC0') as conn:
        ids = dict(case_mod.IDS)
        row = conn.execute("select (select current_deadline::text from public.assignments where id = %s),"
                           " (select current_deadline::text from public.assignments where id = %s)",
                           (ids['A1'], ids['AR'])).fetchone()
        conn.rollback()
        ids['A1_DL'], ids['AR_DL'] = row
        return [run_case(conn, c, ids) for c in case_mod.CASES]


def summarise(results: list[dict]) -> dict:
    controls = [r for r in results if r['kind'] == 'control']
    attacks = [r for r in results if r['kind'] != 'control']
    by_claim = {}
    for r in results:
        b = by_claim.setdefault(r['claim'], {'cases': 0, 'counterexamples': [], 'control_failures': []})
        b['cases'] += 1
        if r['counterexample']:
            b['counterexamples'].append(r['id'])
        if r['kind'] == 'control' and r['verdict'] == 'FAIL':
            b['control_failures'].append(r['id'])
    return {
        'cases': len(results), 'attack_cases': len(attacks), 'control_cases': len(controls),
        'counterexamples': [r['id'] for r in attacks if r['verdict'] == 'FAIL'],
        'control_failures': [r['id'] for r in controls if r['verdict'] == 'FAIL'],
        'run_valid': all(r['verdict'] == 'PASS' for r in controls),
        'by_claim': by_claim,
    }


def write(name: str, payload: dict, text: str) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    base = RAW / f'{stamp}-{name}'
    base.with_suffix('.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    base.with_suffix('.txt').write_text(text, encoding='utf-8')
    return base


def text_report(title: str, env: dict, results: list[dict], summary: dict) -> str:
    lines = [f'# {title}', '']
    lines += [f'{k}: {v}' for k, v in env.items() if k != 'input_sha256']
    lines += ['input sha256:'] + [f'  {k}: {v}' for k, v in env['input_sha256'].items()] + ['']
    lines.append(f"{'id':7} {'claim':5} {'kind':8} {'actor':5} {'expect':6} {'verdict':7} {'rows':>4}  error / note")
    for r in results:
        err = f"[{r['error']['sqlstate']}] {r['error']['message']}" if r['error'] else ''
        note = '' if r['state_check'] else ' STATE CHECK FAILED'
        flag = '  <-- COUNTEREXAMPLE' if r['counterexample'] else ('  <-- CONTROL FAILED' if r['kind'] == 'control' and r['verdict'] == 'FAIL' else '')
        rows = '' if r['rowcount'] is None else r['rowcount']
        lines.append(f"{r['id']:7} {r['claim']:5} {r['kind']:8} {r['actor']:5} {r['expect']:6} {r['verdict']:7} {rows!s:>4}  {err[:110]}{note}{flag}")
    lines += ['', f"cases={summary['cases']} attacks={summary['attack_cases']} controls={summary['control_cases']}",
              f"counterexamples={summary['counterexamples']}", f"control_failures={summary['control_failures']}",
              f"run_valid={summary['run_valid']}", '']
    return '\n'.join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', choices=['before', 'after'], default='before')
    ap.add_argument('--runs', type=int, default=3)
    ap.add_argument('--mutants', action='store_true')
    args = ap.parse_args(argv)

    cluster = db.Cluster()
    try:
        if args.mutants:
            return run_mutants(cluster)
        env = environment(cluster, args.config)
        verdicts = []
        for k in range(1, args.runs + 1):
            t0 = time.perf_counter()
            uri = cluster.build(f'a5_{args.config}_{k}', db.config_sql(args.config))
            results = run_all(uri)
            summary = summarise(results)
            summary['seconds'] = round(time.perf_counter() - t0, 2)
            payload = {'config': args.config, 'run': k, 'environment': env, 'summary': summary, 'results': results}
            base = write(f'{args.config}-run{k}', payload,
                         text_report(f'A5 {args.config} run {k}', env, results, summary))
            verdicts.append([r['verdict'] for r in results])
            print(f"{args.config} run {k}: counterexamples={summary['counterexamples']} "
                  f"control_failures={summary['control_failures']} valid={summary['run_valid']} -> {base.name}")
        print('deterministic across runs:', all(v == verdicts[0] for v in verdicts))
        return 0
    finally:
        cluster.close()


def run_mutants(cluster: db.Cluster) -> int:
    env = environment(cluster, 'before')
    base_results = run_all(cluster.build('a5_mut_base', db.config_sql('before')))
    passing = {r['id'] for r in base_results if r['verdict'] == 'PASS'}
    schema = db.read(db.SCHEMA)
    rows = []
    for m in mutant_mod.MUTANTS:
        mutated = mutant_mod.apply(schema, m)
        if mutated is None:
            rows.append({**m, 'status': 'INVALID', 'killed_by': []})
            continue
        try:
            res = run_all(cluster.build(f"a5_{m['id'].lower()}", db.config_sql('before', mutated)))
        except RuntimeError as exc:
            rows.append({**m, 'status': 'BUILD_ERROR', 'killed_by': [], 'detail': str(exc)})
            continue
        killed_by = [r['id'] for r in res if r['id'] in passing and r['verdict'] == 'FAIL']
        rows.append({**m, 'status': 'KILLED' if killed_by else 'SURVIVED', 'killed_by': killed_by})
    valid = [r for r in rows if r['status'] in ('KILLED', 'SURVIVED')]
    killed = sum(r['status'] == 'KILLED' for r in valid)
    score = round(killed / len(valid), 3) if valid else None
    payload = {'environment': env, 'baseline_passing': sorted(passing), 'mutants': rows,
               'killed': killed, 'valid': len(valid), 'score': score}
    lines = ['# A5 mutation run (oracle check)', ''] + [f'{k}: {v}' for k, v in env.items() if k != 'input_sha256'] + ['']
    for r in rows:
        lines.append(f"{r['id']} {r['status']:9} {r['guard']}  killed_by={','.join(r['killed_by']) or '-'}")
    lines += ['', f'mutation score = {killed}/{len(valid)} = {score}', '']
    base = write('mutants', payload, '\n'.join(lines))
    print('\n'.join(lines[-(len(rows) + 3):]), '->', base.name)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
