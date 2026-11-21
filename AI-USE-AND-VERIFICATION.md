# AI Use and Verification Log

## Tool

| Tool | Used for |
|---|---|
| Claude Code (Anthropic, model Claude Opus 5.5) in VS Code, 2026-11-21 | Reviewing A1–A4 and the target app; proposing the claim; writing the shim, fixtures, cases, mutants, harness, notebook, figures, report and documents; running every command on the author's machine |

The author chose the target system and the scope. The author is responsible for every file.

## Advice accepted, rejected, and AI mistakes

| # | AI suggestion / output | Decision | Reason / independent check |
|---|---|---|---|
| 1 | First proposal: attack the A4 slice (mutation testing of `service.py`) | **Rejected** by the author in favour of the full app repository | The full app has three roles and a deployed architecture, so the privilege tests are more meaningful. The AI agreed after reading its schema |
| 2 | Test against the author's live Supabase project | **Rejected** | Not freezable or reproducible, and it would attack a deployed service with public test accounts. The study uses a throw-away local PostgreSQL |
| 3 | Use the Supabase local stack (Docker) | **Not possible** | No Docker on the machine. A minimal shim was used instead (`harness/supabase_shim.sql`), and this fidelity limit is stated as RR6 |
| 4 | Do not edit the original app repository; copy a hashed snapshot | **Accepted** (author's instruction) | `target/SNAPSHOT-SHA256.txt`; the notebook re-verifies all 62 hashes |
| 5 | AI suspected that a revoked instructor could read enrolled students' profiles (IN-06) | **Refuted by the run** | The policy's sub-query is itself filtered by `enrollments` RLS. Kept as a rejected candidate in the report |
| 6 | AI suspected course update/delete were missing the approval check (IN-04/05/10) | **Confirmed by the run** | 3/3 identical baseline runs; state oracle shows rows actually changed |
| 7 | Fix alternative: also hide the course from revoked instructors (`courses_select`) | **Rejected** | Not needed to remove the counterexamples, and it is a product decision. Kept bounded; recorded as RR3 |
| 8 | Fix alternative: block revocation while the instructor owns courses, or `ON DELETE RESTRICT` | **Rejected** | Changes admin workflow or blocks legitimate deletes; larger than one bounded change |
| 9 | **AI mistake:** invalid UUID (`…0g0001`) in the fixtures | Fixed **before** the freeze | Spotted on re-read; no run was affected |
| 10 | **AI mistake:** protocol case counts (46/8/12) did not match `cases.py` (49/6/11) | Fixed **before** the freeze | Counted programmatically before the freeze |
| 11 | **AI mistake (harness defect):** time-zone name `UTC` is unknown to the Windows PostgreSQL build | Fixed **after** the freeze as deviation **D1** | First baseline attempt executed no case; one-line fix logged in `protocol/DEVIATIONS.md` |
| 12 | **AI weakness in case design:** GR-09 (`javascript:` link) passed only because that assignment was already graded | Disclosed; **post-hoc** PH-01 added | PH-01 shows the link check works. Not counted (frozen-case rule) |
| 13 | **AI weakness:** GR-08 used a non-existent file, so mutant M08 survived | Disclosed; post-hoc PH-02 kills M08 | RR4: add PH-02 to the next frozen case set |
| 14 | **AI mistake:** wrong number ("53") in the notebook conclusion | Corrected to 41 | Recounted from `comparison.csv` |

## Independent verification performed

- Every denial in the baseline was checked by reading its error message, to confirm it came from the intended guard
  and not from a harness error (`results/raw/*before-run1.txt`).
- Each configuration was run 3 times with identical verdicts. The notebook re-runs both configurations in-process,
  and its verdicts equal the recorded raw results.
- Mutation run: 8 of 10 deliberately weakened guards were detected.
- Rollback check: improvement + `rollback/001_down.sql` reproduces exactly the baseline counterexamples
  (`results/raw/20261121-rollback-check.txt`).
- `results/COMPARISON.md` and `fig4-results.png` are generated from the raw JSON, not typed.

## Not performed

- No human peer review of the cases.
- No test on real Supabase (PostgREST, GoTrue, Storage API) or on the live deployment.
- The fix was not deployed to the live project; that is the owner's action (RESIDUAL-RISK.md, recovery step 1).
