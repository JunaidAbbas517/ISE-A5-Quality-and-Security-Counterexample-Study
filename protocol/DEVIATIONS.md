# Deviations from the frozen protocol

Only harness defects may be fixed after the freeze (PROTOCOL.md section 8). Oracles, expectations, cases,
fixtures and thresholds are unchanged by every entry below.

| # | Date (UTC) | File | Change | Why it is a harness defect |
|---|---|---|---|---|
| D1 | 2026-11-21 | `harness/run_study.py` | Session time zone `TimeZone=UTC` -> `TimeZone=UTC0` | The pgserver Windows build ships no IANA time-zone names, so the first baseline attempt could not connect (`invalid value for parameter "TimeZone": "UTC"`) and executed no case. `UTC0` is the POSIX spelling of the same zone (offset +00, verified). No verdict depends on the zone name |
| D2 | 2026-11-21 (after all runs) | `PROTOCOL.md` | Wording only: two sentences that referred to the local version-control history were reworded to point to `protocol/FROZEN-SHA256.txt` | Documentation, not harness or oracle: no case, threshold, oracle or stopping rule changed. The exact frozen text is kept as `protocol/PROTOCOL-as-frozen.md`; its SHA-256 equals the PROTOCOL.md entry in `FROZEN-SHA256.txt` (checked in the notebook) |

**Note on the `git` field in raw headers.** During the study the folder was under local version control, so raw
headers contain local commit IDs and a `dirty` flag (baseline and mutation runs: `dirty = true`, because the D1 edit
was not yet saved in that history). That local history was not published; the authoritative freeze record is
`protocol/FROZEN-SHA256.txt`. Every raw result's `input_sha256` matches it for `cases.py`, `fixtures.sql`,
`supabase_shim.sql` and `mutants.py`; only `run_study.py` differs, by the D1 line.

**Post-hoc cases.** `harness/posthoc.py` (PH-01, PH-02) was written after seeing the baseline. Per section 8 it is
reported separately and not counted in the before/after comparison.
