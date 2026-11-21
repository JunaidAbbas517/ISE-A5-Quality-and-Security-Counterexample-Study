"""POST-HOC cases, written AFTER the baseline was seen (PROTOCOL.md section 8).

They are NOT part of a5-cases-v1 and are NOT counted in the before/after comparison. They exist because the
baseline review found two weak frozen cases:
  * GR-09 passed for an unrelated reason (the assignment was already graded), so the link check was never reached.
  * Mutant M08 (file path ownership check weakened) survived, because GR-08 used a file that does not exist.

  python harness/posthoc.py     # runs PH cases on before, after, and on mutant M08
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402
import mutants as mutant_mod  # noqa: E402
import run_study  # noqa: E402

POSTHOC = [
    dict(id='PH-01', claim='C7', kind='boundary', actor='S1',
         sql="select public.submit_assignment('{A1}', 'x', 'javascript:alert(1)', "
             "'[{{\"path\":\"{A1}/{S1}/u1/report.pdf\",\"name\":\"report.pdf\"}}]'::jsonb)",
         expect='error', check="UNCHANGED(submissions)"),
    dict(id='PH-02', claim='C7', kind='abuse', actor='S1',
         sql="select public.submit_assignment('{A1}', 'x', null, "
             "'[{{\"path\":\"{A3}/{S2}/u2/er.pdf\",\"name\":\"er.pdf\"}}]'::jsonb)",
         expect='error', check="UNCHANGED(submissions)"),
]


def main() -> int:
    run_study.case_mod.CASES = POSTHOC  # run only the post-hoc list through the same oracle
    cluster = db.Cluster()
    try:
        m08 = next(m for m in mutant_mod.MUTANTS if m['id'] == 'M08')
        configs = {
            'before': db.config_sql('before'),
            'after': db.config_sql('after'),
            'mutant-M08': db.config_sql('before', mutant_mod.apply(db.read(db.SCHEMA), m08)),
        }
        lines = ['# A5 POST-HOC cases (not counted in the before/after comparison)', '']
        payload = {'note': 'post-hoc, not counted', 'runs': {}}
        for name, steps in configs.items():
            res = run_study.run_all(cluster.build(f"a5_ph_{name.replace('-', '_').lower()}", steps))
            payload['runs'][name] = res
            for r in res:
                err = f"[{r['error']['sqlstate']}] {r['error']['message']}" if r['error'] else ''
                lines.append(f"{name:11} {r['id']} {r['verdict']}  {err}")
        base = run_study.write('posthoc', payload, '\n'.join(lines) + '\n')
        print('\n'.join(lines), '->', base.name)
        return 0
    finally:
        cluster.close()


if __name__ == '__main__':
    raise SystemExit(main())
