-- A5 bounded improvement (the only one allowed by PROTOCOL.md section 7).
-- Applied as a migration after the frozen schema; the frozen schema file itself is not edited.
--
-- Counterexamples fixed (baseline run): IN-04 rename, IN-05 delete, IN-10 archive.
-- Cause: courses_update and courses_delete only checked ownership (instructor_id = auth.uid()), not that the
-- owner is still an APPROVED instructor. Every other instructor rule uses public.is_instructor_of(), which does.
-- A revoked instructor could therefore delete their course, and the delete cascades to the students'
-- enrolments, assignments, submissions and grades.
--
-- Change: use the same public.is_instructor_of(id) guard as assignments_* policies.
-- Not changed (deliberately): courses_select. A revoked instructor can still see the name of the course they
-- created; hiding it is a product decision, not needed to remove the counterexamples (see RESIDUAL-RISK.md).

drop policy courses_update on public.courses;
create policy courses_update on public.courses for update to authenticated
  using (instructor_id = (select auth.uid()) and public.is_instructor_of(id))
  with check (instructor_id = (select auth.uid()) and public.is_instructor_of(id));

drop policy courses_delete on public.courses;
create policy courses_delete on public.courses for delete to authenticated
  using (instructor_id = (select auth.uid()) and public.is_instructor_of(id));
