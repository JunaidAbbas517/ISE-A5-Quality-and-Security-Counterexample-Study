"""Frozen mutation set a5-mutants-v1: each mutant removes or weakens ONE security guard in the app schema.

Purpose: check the oracle. If the frozen case set cannot tell a weakened schema from the real one, a
"0 violations" result would mean nothing. A mutant is KILLED when at least one case that passes on the
unmutated configuration fails on the mutant. Each `find` text must occur exactly once in schema.sql,
otherwise the mutant is recorded as INVALID (not silently skipped).
"""

MUTANTS = [
    dict(id='M01', guard='change_deadline(): instructor-of-course check removed',
         find="if not public.is_instructor_of(v_course) then",
         replace="if false then"),
    dict(id='M02', guard='profiles: column privilege widened from full_name to all columns',
         find="grant update (full_name) on public.profiles to authenticated;",
         replace="grant update on public.profiles to authenticated;"),
    dict(id='M03', guard='handle_new_user(): requested role copied from sign-up metadata',
         find="case when v_instructor then 'instructor' else 'student' end,",
         replace="coalesce(new.raw_user_meta_data ->> 'requested_role', 'student'),"),
    dict(id='M04', guard='grades_select: returned_at condition removed',
         find="(student_id = (select auth.uid()) and returned_at is not null)",
         replace="(student_id = (select auth.uid()))"),
    dict(id='M05', guard='courses_select: open to every signed-in user',
         find="  instructor_id = (select auth.uid()) or public.is_enrolled_in(id)\n);",
         replace="  true\n);"),
    dict(id='M06', guard="is_instructor_of(): approval status ('active') check removed",
         find="      and p.role = 'instructor' and p.status = 'active'\n  );",
         replace="      and p.role = 'instructor'\n  );"),
    dict(id='M07', guard='change_deadline(): stale expected_previous check removed',
         find="if v_current <> p_expected_previous then",
         replace="if false then"),
    dict(id='M08', guard='submit_assignment(): file path ownership check weakened',
         find="if v_path is null or v_path not like v_a.id::text || '/' || v_me::text || '/%' then",
         replace="if v_path is null then"),
    dict(id='M09', guard='anon: table privileges no longer revoked (RLS still on)',
         find="revoke all on all tables in schema public from anon;",
         replace="-- (mutant M09) revoke removed"),
    dict(id='M10', guard='set_instructor_status(): admin check removed',
         find="if not public.is_admin() then\n    raise exception 'Only an admin can verify instructors';",
         replace="if false then\n    raise exception 'Only an admin can verify instructors';"),
]


def apply(schema: str, mutant: dict) -> str | None:
    """Return the mutated schema, or None if `find` does not occur exactly once."""
    if schema.count(mutant['find']) != 1:
        return None
    return schema.replace(mutant['find'], mutant['replace'])
