# ISE-A5 | Quality and Security Counterexample Study

**Course:** Intelligent Software Engineering | **Due:** 2026-11-23 16:30 (Asia/Shanghai)
**Main report:** [report/ISE-A5-Final-Report.pdf](report/ISE-A5-Final-Report.pdf) (editable: `report/ISE-A5-Final-Report.docx`)

## The study in one paragraph

The deadline-management app built for this project (React + Supabase) claims that the **database enforces every
role boundary**, so the UI is not trusted. We tried to **falsify** that claim. Before running anything, we froze a
protocol: 67 privilege, abuse, boundary and fault-injection cases across 8 actors, 10 mutants, thresholds and a
stopping rule. We then ran the cases against the app's real `schema.sql` on a local PostgreSQL database. **The
baseline falsified one sub-claim:** an instructor whose approval was **revoked** can still rename, archive and
**delete** their course through the REST API, and the delete cascades to students' work and grades. One bounded
migration (two policies) removed all three counterexamples without breaking any control. The other six sub-claims
were not falsified (mutation score 0.80).

| | Before (frozen app) | After (+ migration 001) |
|---|---|---|
| Counterexamples (56 attack cases) | **3**: IN-04 rename, IN-05 delete, IN-10 archive | **0** |
| Controls passing (11) | 11 | 11 |
| Identical verdicts over 3 runs | yes | yes |

Details: [results/COMPARISON.md](results/COMPARISON.md) (generated from raw results).

## Deliverables

| Required | Where |
|---|---|
| Threat/fault model | [THREAT-MODEL.md](THREAT-MODEL.md) |
| Frozen experimental protocol | [PROTOCOL.md](PROTOCOL.md), frozen before execution; file hashes in `protocol/FROZEN-SHA256.txt` (each raw result records the hashes it used); deviations in [protocol/DEVIATIONS.md](protocol/DEVIATIONS.md); exact frozen protocol text in `protocol/PROTOCOL-as-frozen.md` |
| Raw test/scan/mutation results | [results/raw/](results/raw/): 3 baseline runs, 3 after-runs, mutation run, post-hoc run, rollback check (JSON + text) |
| Before/after comparison | [results/COMPARISON.md](results/COMPARISON.md), `results/comparison.csv`, report section 5 |
| Residual risk and recovery plan | [RESIDUAL-RISK.md](RESIDUAL-RISK.md) |
| Notebook (executed) | [notebook/ISE-A5-Study.ipynb](notebook/ISE-A5-Study.ipynb): re-runs the procedure and checks the verdicts against the raw results |
| Report (PDF + Word) | [report/](report/), with flow figures in `report/figures/` |
| AI-use log | [AI-USE-AND-VERIFICATION.md](AI-USE-AND-VERIFICATION.md) |
| Platform summary | [PLATFORM-SUBMISSION.md](PLATFORM-SUBMISSION.md) |

## Repository layout

```
target/app-under-test/   frozen copy of the app (commit 417efd1), never edited; hashes in target/SNAPSHOT-SHA256.txt
harness/                 supabase_shim.sql, fixtures.sql, cases.py, mutants.py, run_study.py, compare.py, posthoc.py
improvement/             001_…sql = the one bounded fix;  rollback/001_down.sql = its exact undo
results/raw/             every run, including the first one, which recorded no results (deviation D1)
notebook/  report/       executed notebook; report source, figures, DOCX, PDF
```

## Reproduce (Windows 11, CPython 3.12.4; about 2 minutes)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python harness\run_study.py --config before --runs 3
.venv\Scripts\python harness\run_study.py --mutants
.venv\Scripts\python harness\run_study.py --config after --runs 3
.venv\Scripts\python harness\compare.py
```

See [REPRODUCE.md](REPRODUCE.md) for the notebook, report rebuild and expected output. Nothing connects to the
internet or to a live Supabase project. The database is a throw-away local PostgreSQL cluster.

## Provenance and scope

- The code under test comes from the author's repository
  `JunaidAbbas517/Centralized-Student-Assignment-and-Deadline-Management-System` at commit
  `417efd15c7651b1e8d6eba2f9016af0ea3300dcf`. That repository was **not modified**. The fix lives only in
  `improvement/` here (see RESIDUAL-RISK.md, RR1).
- All data is synthetic (`*.invalid` emails, fixed UUIDs). No real users, no credentials.
- The database is a stand-in, not real Supabase. `harness/supabase_shim.sql` reproduces only roles, `auth.uid()`, default
  grants and `storage.objects`. PostgREST, GoTrue, the Storage API and the live site were not tested.
- Continuity: A1 problem → A2 invariants (owner-only changes, versioned history) → A3 Todoman investigation →
  A4 local verification slice → **A5 attacks the deployed-architecture version of the same rules**.
