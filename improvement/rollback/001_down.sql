-- Rollback for improvement 001: restores the original course policies exactly as in the frozen schema.
-- Use only if the improvement causes a problem in production; it re-opens counterexamples IN-04/05/10.
-- (Kept in a sub-folder so harness/db.py does not apply it as part of the 'after' configuration.)

drop policy courses_update on public.courses;
create policy courses_update on public.courses for update to authenticated
  using (instructor_id = (select auth.uid())) with check (instructor_id = (select auth.uid()));

drop policy courses_delete on public.courses;
create policy courses_delete on public.courses for delete to authenticated using (instructor_id = (select auth.uid()));
