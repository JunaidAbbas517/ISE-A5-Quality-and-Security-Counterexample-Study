import nbformat as nbf
nb = nbf.v4.new_notebook()
md = nbf.v4.new_markdown_cell; code = nbf.v4.new_code_cell
nb.cells = [
md(r"""# ISE-A5 Quality and Security Counterexample Study: reproduction notebook

This notebook re-executes the **frozen procedure** top to bottom, in-process, and checks the fresh verdicts against
the recorded raw results in `results/raw/`. It writes nothing to `results/raw/`; the recorded runs are made by
`harness/run_study.py` (see REPRODUCE.md).

Run from the repository root with the study environment: `.venv\Scripts\jupyter-nbconvert --to notebook --execute --inplace notebook/ISE-A5-Study.ipynb`"""),
code("""import hashlib, json, os, sys, platform
from pathlib import Path
ROOT = Path.cwd() if (Path.cwd() / 'PROTOCOL.md').exists() else Path.cwd().parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT / 'harness'))
import db, cases, mutants, run_study
print('python', sys.version.split()[0], '|', platform.platform())
print('cases', len(cases.CASES), '| mutants', len(mutants.MUTANTS))"""),
md("## 1. The code under test is the untouched snapshot"),
code("""bad = []
for line in (ROOT / 'target' / 'SNAPSHOT-SHA256.txt').read_text().splitlines():
    digest, name = line.split(maxsplit=1)
    p = ROOT / 'target' / 'app-under-test' / name.lstrip('*').removeprefix('./')
    if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
        bad.append(name)
print('snapshot files checked; mismatches:', bad or 'none')
assert not bad"""),
md("## 2. Frozen inputs match the freeze record"),
code("""frozen = {}
for line in (ROOT / 'protocol' / 'FROZEN-SHA256.txt').read_text().splitlines():
    d, n = line.split(maxsplit=1); frozen[n.lstrip('*')] = d
for n, d in frozen.items():
    now = hashlib.sha256((ROOT / n).read_bytes()).hexdigest()
    print(('same   ' if now == d else 'CHANGED'), n)
print()
print('Expected: harness/run_study.py differs (D1) and PROTOCOL.md differs (D2, wording only).')
orig = hashlib.sha256((ROOT / 'protocol' / 'PROTOCOL-as-frozen.md').read_bytes()).hexdigest()
print('protocol/PROTOCOL-as-frozen.md equals the frozen PROTOCOL.md hash:', orig == frozen['PROTOCOL.md'])
assert orig == frozen['PROTOCOL.md']"""),
md("## 3. Re-run baseline and improved configurations"),
code("""cluster = db.Cluster()
fresh = {}
try:
    for cfg in ('before', 'after'):
        fresh[cfg] = run_study.run_all(cluster.build(f'nb_{cfg}', db.config_sql(cfg)))
        s = run_study.summarise(fresh[cfg])
        print(f"{cfg:6}: counterexamples={s['counterexamples']}  control_failures={s['control_failures']}  valid={s['run_valid']}")
    m08 = None
finally:
    cluster.close()"""),
md("## 4. Fresh verdicts equal the recorded verdicts"),
code("""def recorded(cfg):
    f = sorted((ROOT / 'results' / 'raw').glob(f'*-{cfg}-run1.json'))[-1]
    return f.name, {r['id']: r['verdict'] for r in json.loads(f.read_text(encoding='utf-8'))['results']}
for cfg in ('before', 'after'):
    name, rec = recorded(cfg)
    diff = [r['id'] for r in fresh[cfg] if rec[r['id']] != r['verdict']]
    print(f'{cfg:6} vs {name}: differences = {diff or "none"}')
    assert not diff"""),
md("## 5. Counterexamples in detail"),
code("""for r in fresh['before']:
    if r['counterexample']:
        print(r['id'], r['actor'], 'rows affected =', r['rowcount'], '| state unchanged =', r['state_check'])
print()
print(next(c['sql'] for c in cases.CASES if c['id'] == 'IN-05'))"""),
md("## 6. The bounded improvement"),
code("""print((ROOT / 'improvement' / '001_require_active_instructor_for_course_writes.sql').read_text())"""),
md("## 7. Comparison (generated from raw results) and figures"),
code("""import subprocess
print(subprocess.run([sys.executable, 'harness/compare.py'], capture_output=True, text=True, encoding='utf-8').stdout)"""),
code("""from IPython.display import Image, display
for f in sorted((ROOT / 'report' / 'figures').glob('*.png')):
    print(f.name); display(Image(filename=str(f), width=820))"""),
md("""## 8. Conclusion

- Sub-claim **C4** ("a pending or rejected instructor can manage nothing") is **falsified** on the frozen app:
  IN-04 rename, IN-05 delete (with cascade), IN-10 archive.
- One migration (two policies) removes all three. All 11 controls still pass, and no new counterexample appears.
- The other six sub-claims were **not falsified** by their 41 attack cases (the other 12 C4 attacks also held). The mutation score is 0.80, exactly at the
  threshold, and two survivors are explained in RESIDUAL-RISK.md. Not falsified does not mean proven."""),
]
nb.metadata['kernelspec'] = {'name': 'ise-a5', 'display_name': 'ISE-A5 (.venv)', 'language': 'python'}
nbf.write(nb, 'notebook/ISE-A5-Study.ipynb')
