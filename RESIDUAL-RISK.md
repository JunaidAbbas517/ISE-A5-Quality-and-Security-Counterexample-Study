# Residual Risk and Recovery Plan

## What the study showed

- **Falsified:** sub-claim C4, "a pending or rejected instructor can manage nothing". A revoked instructor could
  rename (IN-04), archive (IN-10) and **delete** (IN-05) the course they created. Deleting cascades to the course's
  enrolments, assignments, submissions and grades. The UI hides this (non-active instructors only see "Waiting for
  approval"), but the REST API with the public anon key does not.
- **Fixed in this repository only:** `improvement/001_…sql` adds the approved-instructor guard. With it, the identical
  procedure gives 0 counterexamples and all 11 controls still pass.
- **Not falsified** (56 attack cases, mutation score 0.80): C1, C2, C3, C5, C6, C7. "Not falsified" means these
  cases found no violation. It does not prove the rules are correct.

## Residual risks

| # | Risk | Likelihood / impact | Why it remains | Next action |
|---|---|---|---|---|
| RR1 | **The live Supabase project still has the hole.** The fix exists only here; the original app repository was deliberately not changed | Medium / **High** (data loss for every student in the course) | Out of scope by the owner's choice | Apply migration 001 to the live project (recovery plan, step 1) |
| RR2 | **Public one-click test logins on the deployed site**, including an **admin** account with a published password (`VITE_SHOW_TEST_ACCOUNTS=true`, README) | High / High | Live site out of scope; not tested | Remove the flag, change or delete the seed accounts before real users join |
| RR3 | A revoked instructor can still **read** their old course row (name, code, enrolment code) | Medium / Low | `courses_select` left unchanged on purpose (bounded fix); hiding it is a product decision | Decide policy; if required, add `is_instructor_of(id)` to `courses_select` |
| RR4 | **Test gap:** the frozen suite did not detect weakening of the file-ownership check in `submit_assignment()` (mutant M08 survived) | Low / Medium | GR-08 used a non-existent file, so another check stopped it | Add post-hoc PH-02 to the next frozen case set (it kills M08) |
| RR5 | GR-09 (`javascript:` link) passed for an unrelated reason (the assignment was already graded) | Low / Low | Weak case design | PH-01 shows the link check works; replace GR-09 in the next case set |
| RR6 | **Stand-in fidelity:** local PostgreSQL 16.2 plus a shim, not real Supabase/PostgREST/Storage | Medium / Medium | No Docker on the study machine; offline reproducibility preferred | Rerun `run_study.py` against a Supabase local stack or a staging project |
| RR7 | 8-character hexadecimal enrolment codes (32 bits) with no rate limit on `enroll_by_code()` | Low / Medium | Brute force out of scope | Rate limiting or longer codes |
| RR8 | Deleting a course leaves files in Storage (rows are not cascaded) | Medium / Low | Storage API behaviour, not tested | Clean up through the Storage API before deletion (the app's own comment says so) |
| RR9 | No audit log of who deleted what | High / Medium | Not part of the schema | Add an audit trigger on `courses` / `assignments` deletes |

## Recovery plan

**1. Deploy the fix (owner action, about 10 minutes)**
1. Take a backup first (Supabase Dashboard → Database → Backups, or `pg_dump`).
2. Run `improvement/001_require_active_instructor_for_course_writes.sql` in the Supabase SQL editor.
3. Verify in the dashboard that `courses_update` and `courses_delete` now contain `is_instructor_of(id)`.
4. Verify behaviour: as an active instructor, rename a course (must work). As a revoked test instructor, call
   `PATCH /rest/v1/courses?id=eq.<id>` with their JWT (must return an empty array, with no change).

**2. Check whether the hole was already used**
- Compare current courses with the latest backup. Look for courses whose owner has `status = 'rejected'` and that
  changed or disappeared after the revocation date.
- Look in the Supabase API logs for `DELETE`/`PATCH` on `/rest/v1/courses` by users whose status is `rejected`.

**3. If it was used**
- Restore the affected course and its cascaded rows from the backup (point-in-time restore if available, otherwise
  restore to a separate database and copy the rows back).
- Ban or delete the revoked account in Supabase Auth so its refresh token stops working.
- Tell the affected instructor and students what was restored.

**4. If the fix causes a problem**
- Run `improvement/rollback/001_down.sql`. It restores the original policies exactly, which re-opens RR1, so fix
  forward quickly.
- Expected side effects are minimal: all 11 controls pass after the fix, including re-approval (IN-15) and
  active-instructor edits (IN-16), and the UI never offers these actions to non-active instructors.
