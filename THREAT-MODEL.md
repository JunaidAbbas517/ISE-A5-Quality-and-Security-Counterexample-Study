# Threat and Fault Model

**System under test:** the Student Assignment and Deadline Management System, frozen at commit
`417efd15c7651b1e8d6eba2f9016af0ea3300dcf` (see [target/UPSTREAM.md](target/UPSTREAM.md)).
React front end + Supabase (Auth, PostgreSQL with row-level security (RLS), Storage).

## Why the database is the security boundary

The browser app ships the public **anon key**. Anyone can take that key, sign up and send their own requests to
the Supabase REST API (PostgREST) or call any granted RPC function directly. The UI hides buttons, but hiding is not
enforcement. So **every rule must hold in PostgreSQL itself**: RLS policies, column privileges and the checks inside
`security definer` functions. PostgREST runs each request as `SET LOCAL ROLE anon|authenticated` with the user ID from the
JWT, and this study sends requests the same way.

```
 attacker's own client --anon key + own JWT--> PostgREST --SET ROLE authenticated, sub=<uid>--> PostgreSQL
 (curl, script, devtools)                      (no rules of its own)                      RLS + grants + RPC checks
                                                                                          = the only enforcement
```

## Assets

| Asset | Why it matters |
|---|---|
| Assignment deadlines and their history | The project's core value (A1–A4): a deadline must change only by the course instructor, with history and notifications |
| Course integrity (courses, enrolments, assignments, submissions, grades) | Deleting a course cascades to all of its students' work and grades |
| Grades before release | Students must not see a draft grade |
| Student personal data (name, email) | Privacy |
| Roles and approval status | Every other rule depends on them |

## Actors (attackers are signed-in users acting outside their role)

| Actor | Fixture | Can legitimately |
|---|---|---|
| Anonymous (anon key, no login) | `anon` | Nothing |
| Student | S1 (in C1 and CR), S2 (in C2) | See own courses and work, submit, see returned grades |
| Active instructor | T1 (owns C1), T2 (owns C2) | Manage **own** courses only |
| Pending instructor | P | Nothing until approved |
| **Revoked instructor** (approved, built a course, then set to `rejected`) | R (owns CR) | Nothing: README says a pending or rejected instructor "can manage nothing" |
| Admin | A | Approve and revoke instructors, read platform stats |
| Supabase Auth service (sign-up) | `auth` | Creates a profile from sign-up metadata, which the user controls |

## Attack model (what the cases try)

1. **Privilege escalation:** write role, email or status columns, or self-approve.
2. **Horizontal access:** read or change another student's or another course's rows, files, grades or notifications.
3. **Bypass the official path:** change `current_deadline` or forge `deadline_changes` without `change_deadline()`.
4. **Stale authority:** act with a role that has been taken away (pending or revoked instructor).
5. **Sign-up tampering:** request the `admin` role in user-controlled metadata.
6. **Anonymous access:** read, write or call RPCs with only the anon key.
7. **Boundary input:** stale expected deadline, deadline in the past, marks above maximum, path traversal in
   file references, `javascript:` links, archived enrolment codes.

## Fault model

Fault injection is limited to **one mid-transaction failure** in `change_deadline()`: the notification insert raises.
The oracle is atomicity, meaning the deadline, history and notifications all stay unchanged.

## Trust assumptions (not attacked)

- Supabase Auth issues correct JWTs; the `service_role` key and database password stay secret.
- The project owner or superuser is trusted. RLS does not apply to them.
- PostgREST adds no rules of its own and does not weaken any. It translates requests to SQL.

## Out of scope (stated, not hidden)

- The live deployed site and its public one-click test accounts (`VITE_SHOW_TEST_ACCOUNTS=true`). This is a real
  exposure, but testing the live service is outside an offline, reproducible study (see RESIDUAL-RISK.md).
- Supabase Storage API checks such as size limits and MIME types. Only the `storage.objects` RLS policies are tested.
- Brute-forcing 8-character enrolment codes, rate limiting, denial of service.
- Front-end XSS and session handling; email/PKCE flows.
- Real Supabase internals. A local stand-in ([harness/supabase_shim.sql](harness/supabase_shim.sql)) reproduces only
  what the schema depends on.
