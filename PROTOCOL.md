# Frozen Experimental Protocol

This file, the harness, the cases and the fixtures were fixed **before any test was executed**.
`protocol/FROZEN-SHA256.txt`, written at that moment, lists the hash of every frozen file, and each raw result records
the hashes of the inputs it actually used, so anyone can check that cases, fixtures and oracle did not change.

## 1. The claim under test

> **Main claim.** For any client holding the public anon key, the database enforces every role boundary the
> application documents. No signed-in or anonymous user can read or change data outside their role.

Sources: the app's README "Security notes" and "Roles" sections and the comments in `supabase/schema.sql`.
The claim is split into seven sub-claims, so a counterexample points to a specific rule:

| ID | Sub-claim (quoted or paraphrased from the app) | Cases |
|---|---|---|
| C1 | "Role, email … cannot be changed directly from the client"; users may only edit their name | PR-01..06 |
| C2 | "Deadlines change only through `change_deadline()`", in one transaction, by the course instructor | DL-01..10 |
| C3 | "Students cannot list courses they are not in"; users see only their own work | IS-01..13 |
| C4 | "A pending or rejected [instructor] can manage nothing" | IN-01..18 |
| C5 | "Admin can never be chosen at sign-up" | SU-01..02 |
| C6 | "The anonymous (logged-out) role gets nothing at all" | AN-01..07 |
| C7 | Students see a grade only once it is returned; submissions and grades are written only by RPCs | GR-01..11 |

## 2. Frozen environment

| Item | Value |
|---|---|
| Code under test | `target/app-under-test/` = commit `417efd1…`, 62 files, hashes in `target/SNAPSHOT-SHA256.txt`. Never edited |
| Database | PostgreSQL 16.2 started by `pgserver==0.1.4`, a fresh throw-away cluster and database per run |
| Supabase stand-in | `harness/supabase_shim.sql`: roles, `auth.uid()`, default grants, `storage.objects` + `storage.foldername()` |
| Runtime | CPython 3.12.4, `psycopg==3.3.9`, Windows 11; full pins in `requirements.txt` |
| Data | `harness/fixtures.sql` = `a5-fixtures-v1`, synthetic only (`*.invalid` emails), fixed UUIDs |
| Randomness | None affects verdicts. Fixed UUIDs; deadlines are relative to build time; session time zone UTC |

## 3. Baseline

The **baseline** is the frozen schema with no changes (`--config before`). It is executed before any
improvement is written.

## 4. Attack and fault model

See [THREAT-MODEL.md](THREAT-MODEL.md). The case set `a5-cases-v1` (`harness/cases.py`) has 67 cases:

| Kind | Meaning | Count |
|---|---|---|
| abuse | An actor attempts something outside their role (privilege) | 49 |
| boundary | An edge input to a guarded operation | 6 |
| fault | An injected mid-transaction failure in `change_deadline()` | 1 |
| control | Legitimate use that must still work (validity and side-effect check) | 11 |

Plus the mutation set `a5-mutants-v1` (`harness/mutants.py`): 10 single-guard weakenings of the schema.

## 5. Oracle

Each case runs as its actor inside one transaction, with `SET LOCAL ROLE` and the JWT subject set exactly as
PostgREST does, and is then **rolled back**, so cases are independent.

- `expect = error`: the request must raise an error.
- `expect = none`: the request must raise an error, or return or affect **zero** rows (RLS filtering).
- `expect = ok`: the request must succeed with at least one row.
- `check`: a superuser state query that must be true afterwards. `UNCHANGED(t)` compares table `t` row by row with
  a snapshot taken just before the request, so a "denied" request that still changed data is caught.

**Verdict:** PASS only if both the action and the state check hold. A FAIL on an abuse, boundary or fault case is a
**counterexample**. A FAIL on a control makes the run **invalid**.

**Mutation oracle:** a mutant is *killed* if at least one case that passes on the baseline fails on the mutant.

## 6. Thresholds (decided now)

| Decision | Rule |
|---|---|
| Run validity | All 11 controls PASS. An invalid run is reported, not used as evidence |
| Claim falsified | **≥ 1 counterexample** in a valid run falsifies that sub-claim and therefore the main claim |
| Claim survives | 0 counterexamples in a valid run **and** mutation score ≥ 0.80 (otherwise "inconclusive: oracle too weak") |
| Determinism | Each configuration is run 3 times; verdicts must be identical, otherwise reported as flaky |
| Improvement accepted | After-run is valid (all controls pass), the targeted counterexamples are gone, and **no new** counterexample appears |

## 7. Stopping rule

1. Run the baseline once (3 repetitions) and the mutation set once.
2. Apply **at most one** bounded improvement: one migration file in `improvement/`, applied after the frozen schema.
   It may only change the policies or functions involved in observed counterexamples. Cases, fixtures, oracle and
   thresholds must not change.
3. Run the identical procedure once more on the improved configuration (`--config after`, 3 repetitions).
4. **Stop**, whatever the result. Anything left over goes to RESIDUAL-RISK.md, with no second round of fixes.

## 8. Allowed deviations

Only **harness defects** (a crash, a setup error, or a case that cannot run for a reason unrelated to the claim) may be
fixed after the freeze. Each fix is recorded in `protocol/DEVIATIONS.md` with the reason. A case's
`expect` or `check` may not be changed to turn a FAIL into a PASS. Any new case thought of after seeing results goes
in a separate post-hoc list and is not counted in the before/after comparison.
