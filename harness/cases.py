"""Frozen abuse / privilege / boundary / fault-injection cases (case set a5-cases-v1).

Each case is run as one actor inside its own transaction, which is always rolled back, so cases are independent.

Fields
  id      stable identifier
  claim   which claim (see PROTOCOL.md section 2) the case attacks or controls
  kind    abuse | boundary | fault | control
          abuse/boundary/fault: a FAIL is a counterexample to the claim.
          control: legitimate use that must work; a FAIL means the run (or a fix) is invalid / has a side effect.
  actor   key of ACTORS, 'anon' (logged-out API key) or 'auth' (Supabase Auth service inserting a new user)
  sql     the request, with {PLACEHOLDERS} filled from IDS
  expect  'error'  the request must raise
          'none'   the request must raise OR return/affect zero rows (RLS silently filters)
          'ok'     the request must succeed and return/affect at least one row
  check   SQL run afterwards as superuser that must return true (state oracle). UNCHANGED(t) compares table t
          with a snapshot taken immediately before the request.
  pre     optional superuser SQL run before the request (fault injection / state set-up)
"""

ACTORS = {
    'A': '00000000-0000-0000-0000-000000000a01',
    'T1': '00000000-0000-0000-0000-000000000a11',
    'T2': '00000000-0000-0000-0000-000000000a12',
    'P': '00000000-0000-0000-0000-000000000a21',
    'R': '00000000-0000-0000-0000-000000000a22',
    'S1': '00000000-0000-0000-0000-000000000a31',
    'S2': '00000000-0000-0000-0000-000000000a32',
}

IDS = {
    **ACTORS,
    'C1': '00000000-0000-0000-0000-0000000c0001', 'C2': '00000000-0000-0000-0000-0000000c0002',
    'CR': '00000000-0000-0000-0000-0000000c00ff', 'CX': '00000000-0000-0000-0000-0000000c00aa',
    'A1': '00000000-0000-0000-0000-0000000a0001', 'A2L': '00000000-0000-0000-0000-0000000a0002',
    'A3': '00000000-0000-0000-0000-0000000a0003', 'AR': '00000000-0000-0000-0000-0000000a00ff',
    'SUB1': '00000000-0000-0000-0000-00000005b001', 'SUB2': '00000000-0000-0000-0000-00000005b002',
    'G1': '00000000-0000-0000-0000-0000000d0001', 'G2': '00000000-0000-0000-0000-0000000d0002',
    'NEW1': '00000000-0000-0000-0000-000000000b01', 'NEW2': '00000000-0000-0000-0000-000000000b02',
}

SNAPSHOT_TABLES = ['profiles', 'courses', 'enrollments', 'assignments', 'deadline_changes',
                   'assignment_progress', 'notifications', 'submissions', 'grades']

# Deadline of A1 / AR at fixture build time; filled in by the runner as {A1_DL}, {AR_DL}.
FAULT_TRIGGER = """
create function public.a5_fault() returns trigger language plpgsql as $$
begin raise exception 'A5 injected fault: notification insert failed'; end $$;
create trigger a5_fault before insert on public.notifications
  for each row execute function public.a5_fault();
"""

CASES = [
    # ---- C1: role, email and status cannot be changed from the client --------------------------------
    dict(id='PR-01', claim='C1', kind='abuse', actor='S1',
         sql="update public.profiles set role = 'admin' where id = '{S1}'",
         expect='error', check="UNCHANGED(profiles)"),
    dict(id='PR-02', claim='C1', kind='abuse', actor='S1',
         sql="update public.profiles set email = 'x@evil.invalid' where id = '{S1}'",
         expect='error', check="UNCHANGED(profiles)"),
    dict(id='PR-03', claim='C1', kind='abuse', actor='P',
         sql="update public.profiles set status = 'active' where id = '{P}'",
         expect='error', check="UNCHANGED(profiles)"),
    dict(id='PR-04', claim='C1', kind='abuse', actor='S1',
         sql="update public.profiles set full_name = 'hacked' where id = '{S2}'",
         expect='none', check="UNCHANGED(profiles)"),
    dict(id='PR-05', claim='C1', kind='abuse', actor='S1',
         sql="insert into public.profiles (id, full_name, email, role, status) "
             "values ('{S1}', 'x', 'x', 'admin', 'active')",
         expect='error', check="UNCHANGED(profiles)"),
    dict(id='PR-06', claim='C1', kind='control', actor='S1',
         sql="update public.profiles set full_name = 'Student One B' where id = '{S1}'",
         expect='ok', check="(select full_name = 'Student One B' from public.profiles where id = '{S1}')"),

    # ---- C5: admin can never be chosen at sign-up -------------------------------------------------------
    dict(id='SU-01', claim='C5', kind='abuse', actor='auth',
         sql="insert into auth.users (id, email, raw_user_meta_data) values ('{NEW1}', 'evil@a5.invalid', "
             "'{{\"requested_role\":\"admin\",\"role\":\"admin\",\"status\":\"active\"}}')",
         expect='ok', check="(select role = 'student' and status = 'active' from public.profiles where id = '{NEW1}')"),
    dict(id='SU-02', claim='C5', kind='control', actor='auth',
         sql="insert into auth.users (id, email, raw_user_meta_data) values ('{NEW2}', 'newt@a5.invalid', "
             "'{{\"requested_role\":\"instructor\"}}')",
         expect='ok', check="(select role = 'instructor' and status = 'pending' from public.profiles where id = '{NEW2}')"),

    # ---- C2: current_deadline changes only through change_deadline() (atomic, owner-only, versioned) ---
    dict(id='DL-01', claim='C2', kind='abuse', actor='T1',
         sql="update public.assignments set current_deadline = current_deadline + interval '1 day' where id = '{A1}'",
         expect='error', check="UNCHANGED(assignments) and UNCHANGED(deadline_changes)"),
    dict(id='DL-02', claim='C2', kind='control', actor='T1',
         sql="select public.change_deadline('{A1}', '{A1_DL}'::timestamptz + interval '2 days', '{A1_DL}'::timestamptz, 'extension')",
         expect='ok',
         check="(select current_deadline = '{A1_DL}'::timestamptz + interval '2 days' from public.assignments where id = '{A1}')"
               " and (select count(*) = 1 from public.deadline_changes where assignment_id = '{A1}')"
               " and (select count(*) = 1 from public.notifications where recipient_id = '{S1}'"
               "      and assignment_id = '{A1}' and type = 'deadline_changed')"),
    dict(id='DL-03', claim='C2', kind='abuse', actor='S1',
         sql="select public.change_deadline('{A1}', '{A1_DL}'::timestamptz + interval '2 days', '{A1_DL}'::timestamptz, 'student')",
         expect='error', check="UNCHANGED(assignments) and UNCHANGED(deadline_changes)"),
    dict(id='DL-04', claim='C2', kind='abuse', actor='T2',
         sql="select public.change_deadline('{A1}', '{A1_DL}'::timestamptz + interval '2 days', '{A1_DL}'::timestamptz, 'other teacher')",
         expect='error', check="UNCHANGED(assignments) and UNCHANGED(deadline_changes)"),
    dict(id='DL-05', claim='C2', kind='abuse', actor='R',
         sql="select public.change_deadline('{AR}', '{AR_DL}'::timestamptz + interval '2 days', '{AR_DL}'::timestamptz, 'revoked')",
         expect='error', check="UNCHANGED(assignments) and UNCHANGED(deadline_changes)"),
    dict(id='DL-06', claim='C2', kind='boundary', actor='T1',
         sql="select public.change_deadline('{A1}', '{A1_DL}'::timestamptz + interval '2 days', '{A1_DL}'::timestamptz - interval '1 second', 'stale page')",
         expect='error', check="UNCHANGED(assignments) and UNCHANGED(deadline_changes)"),
    dict(id='DL-07', claim='C2', kind='boundary', actor='T1',
         sql="select public.change_deadline('{A1}', now() - interval '1 day', '{A1_DL}'::timestamptz, 'past')",
         expect='error', check="UNCHANGED(assignments) and UNCHANGED(deadline_changes)"),
    dict(id='DL-08', claim='C2', kind='abuse', actor='T1',
         sql="insert into public.deadline_changes (assignment_id, previous_deadline, new_deadline, changed_by, reason) "
             "values ('{A1}', now(), now() + interval '30 days', '{T2}', 'forged history')",
         expect='error', check="UNCHANGED(deadline_changes)"),
    dict(id='DL-09', claim='C2', kind='fault', actor='T1', pre=FAULT_TRIGGER,
         sql="select public.change_deadline('{A1}', '{A1_DL}'::timestamptz + interval '2 days', '{A1_DL}'::timestamptz, 'fault')",
         expect='error',
         check="UNCHANGED(assignments) and UNCHANGED(deadline_changes) and UNCHANGED(notifications)"),
    dict(id='DL-10', claim='C2', kind='abuse', actor='T1',
         sql="update public.assignments set title = 'taken over' where id = '{A3}'",
         expect='none', check="UNCHANGED(assignments)"),

    # ---- C3: users see and change only their own courses and work -------------------------------------
    dict(id='IS-01', claim='C3', kind='abuse', actor='S2',
         sql="select * from public.courses where id = '{C1}'", expect='none'),
    dict(id='IS-02', claim='C3', kind='abuse', actor='S2',
         sql="select * from public.assignments where course_id = '{C1}'", expect='none'),
    dict(id='IS-03', claim='C3', kind='abuse', actor='S2',
         sql="select * from public.profiles where id = '{S1}'", expect='none'),
    dict(id='IS-04', claim='C3', kind='abuse', actor='S1',
         sql="select * from public.submissions where student_id = '{S2}'", expect='none'),
    dict(id='IS-05', claim='C3', kind='control', actor='S1',
         sql="select * from public.submissions where student_id = '{S1}'", expect='ok'),
    dict(id='IS-06', claim='C3', kind='abuse', actor='S1',
         sql="insert into public.enrollments (student_id, course_id) values ('{S1}', '{C2}')",
         expect='error', check="UNCHANGED(enrollments)"),
    dict(id='IS-07', claim='C3', kind='abuse', actor='S1',
         sql="select * from storage.objects where name like '{A3}/%'", expect='none'),
    dict(id='IS-08', claim='C3', kind='abuse', actor='S1',
         sql="insert into storage.objects (bucket_id, name, metadata) values "
             "('submissions', '{A3}/{S2}/x/evil.pdf', '{{\"size\":1}}')",
         expect='error', check="(select count(*) = 3 from storage.objects where bucket_id = 'submissions')"),
    dict(id='IS-09', claim='C3', kind='abuse', actor='S2',
         sql="select * from public.grades where student_id = '{S1}'", expect='none'),
    dict(id='IS-10', claim='C3', kind='boundary', actor='S1',
         sql="select public.enroll_by_code('CODECXDD')",
         expect='error', check="UNCHANGED(enrollments)"),
    dict(id='IS-11', claim='C3', kind='abuse', actor='S1',
         sql="update public.notifications set is_read = true where recipient_id = '{S2}'",
         expect='none', check="UNCHANGED(notifications)"),
    dict(id='IS-12', claim='C3', kind='control', actor='S1',
         sql="select public.enroll_by_code('  codec2bb ')",
         expect='ok', check="exists (select 1 from public.enrollments where student_id = '{S1}' and course_id = '{C2}')"),
    dict(id='IS-13', claim='C3', kind='abuse', actor='T1',
         sql="select * from public.submissions where assignment_id = '{A3}'", expect='none'),

    # ---- C7: grades visible only once returned; students cannot alter submissions or grades -----------
    dict(id='GR-01', claim='C7', kind='abuse', actor='S1',
         sql="select * from public.grades where id = '{G1}'", expect='none'),
    dict(id='GR-02', claim='C7', kind='control', actor='S1',
         sql="select * from public.grades where id = '{G2}'", expect='ok'),
    dict(id='GR-03', claim='C7', kind='abuse', actor='S1',
         sql="update public.submissions set summary = 'rewritten' where id = '{SUB1}'",
         expect='error', check="UNCHANGED(submissions)"),
    dict(id='GR-04', claim='C7', kind='abuse', actor='S1',
         sql="insert into public.grades (assignment_id, student_id, marks, graded_by, returned_at) "
             "values ('{A3}', '{S1}', 100, '{T2}', now())",
         expect='error', check="UNCHANGED(grades)"),
    dict(id='GR-05', claim='C7', kind='abuse', actor='S1',
         sql="select public.grade_submission('{A1}', '{S1}', 100, 'self-graded', true)",
         expect='error', check="UNCHANGED(grades)"),
    dict(id='GR-06', claim='C7', kind='abuse', actor='S1',
         sql="insert into public.assignment_progress (student_id, assignment_id, status) values ('{S1}', '{A1}', 'completed')",
         expect='error', check="UNCHANGED(assignment_progress)"),
    dict(id='GR-07', claim='C7', kind='boundary', actor='T1',
         sql="select public.grade_submission('{A1}', '{S1}', 101, 'over max', false)",
         expect='error', check="UNCHANGED(grades)"),
    dict(id='GR-08', claim='C7', kind='boundary', actor='S1',
         sql="select public.submit_assignment('{A1}', 'x', null, "
             "'[{{\"path\":\"{A1}/{S1}/../{S2}/u2/er.pdf\",\"name\":\"er.pdf\"}}]'::jsonb)",
         expect='error', check="UNCHANGED(submissions)"),
    dict(id='GR-09', claim='C7', kind='boundary', actor='S1',
         sql="select public.submit_assignment('{A2L}', 'x', 'javascript:alert(1)', '[]'::jsonb)",
         expect='error', check="UNCHANGED(submissions)"),
    dict(id='GR-10', claim='C7', kind='control', actor='S1',
         sql="select public.submit_assignment('{A1}', 'final', null, "
             "'[{{\"path\":\"{A1}/{S1}/u1/report.pdf\",\"name\":\"report.pdf\"}}]'::jsonb)",
         expect='ok', check="exists (select 1 from public.submissions where assignment_id = '{A1}' and student_id = '{S1}' and attempt = 2)"),
    dict(id='GR-11', claim='C7', kind='control', actor='T1',
         sql="select public.grade_submission('{A1}', '{S1}', 90, 'good', true)",
         expect='ok', check="(select marks = 90 and returned_at is not null from public.grades where assignment_id = '{A1}' and student_id = '{S1}')"),

    # ---- C4: a pending or rejected (revoked) instructor can manage nothing ----------------------------
    dict(id='IN-01', claim='C4', kind='abuse', actor='P',
         sql="insert into public.courses (instructor_id, name, course_code) values ('{P}', 'Pending course', 'PX1')",
         expect='error', check="UNCHANGED(courses)"),
    dict(id='IN-02', claim='C4', kind='abuse', actor='R',
         sql="insert into public.courses (instructor_id, name, course_code) values ('{R}', 'New revoked course', 'RX1')",
         expect='error', check="UNCHANGED(courses)"),
    dict(id='IN-03', claim='C4', kind='abuse', actor='R',
         sql="insert into public.assignments (course_id, title, current_deadline) values ('{CR}', 'new hw', now() + interval '3 days')",
         expect='error', check="UNCHANGED(assignments)"),
    dict(id='IN-04', claim='C4', kind='abuse', actor='R',
         sql="update public.courses set name = 'Renamed by revoked instructor' where id = '{CR}'",
         expect='none', check="UNCHANGED(courses)"),
    dict(id='IN-05', claim='C4', kind='abuse', actor='R',
         sql="delete from public.courses where id = '{CR}'",
         expect='none',
         check="UNCHANGED(courses) and UNCHANGED(enrollments) and UNCHANGED(assignments) and UNCHANGED(submissions)"),
    dict(id='IN-06', claim='C4', kind='abuse', actor='R',
         sql="select id, full_name, email from public.profiles where id = '{S1}'", expect='none'),
    dict(id='IN-07', claim='C4', kind='abuse', actor='R',
         sql="select * from public.enrollments where course_id = '{CR}'", expect='none'),
    dict(id='IN-08', claim='C4', kind='abuse', actor='R',
         sql="select public.grade_submission('{AR}', '{S1}', 50, 'revoked grading', true)",
         expect='error', check="UNCHANGED(grades)"),
    dict(id='IN-09', claim='C4', kind='abuse', actor='R',
         sql="select * from public.submissions where assignment_id = '{AR}'", expect='none'),
    dict(id='IN-10', claim='C4', kind='abuse', actor='R',
         sql="update public.courses set archived = true where id = '{CR}'",
         expect='none', check="UNCHANGED(courses)"),
    dict(id='IN-11', claim='C4', kind='abuse', actor='P',
         sql="select public.set_instructor_status('{P}', 'active')",
         expect='error', check="UNCHANGED(profiles)"),
    dict(id='IN-12', claim='C4', kind='abuse', actor='T1',
         sql="select public.set_instructor_status('{P}', 'active')",
         expect='error', check="UNCHANGED(profiles)"),
    dict(id='IN-13', claim='C4', kind='abuse', actor='T1',
         sql="select public.admin_stats()", expect='error'),
    dict(id='IN-14', claim='C4', kind='control', actor='A',
         sql="select public.admin_stats()", expect='ok'),
    dict(id='IN-15', claim='C4', kind='control', actor='R',
         pre="update public.profiles set status = 'active' where id = '{R}'",
         sql="update public.courses set name = 'Revoked Course (re-approved)' where id = '{CR}'",
         expect='ok', check="(select name = 'Revoked Course (re-approved)' from public.courses where id = '{CR}')"),
    dict(id='IN-16', claim='C4', kind='control', actor='T1',
         sql="update public.courses set name = 'Software Testing II' where id = '{C1}'",
         expect='ok', check="(select name = 'Software Testing II' from public.courses where id = '{C1}')"),
    dict(id='IN-17', claim='C4', kind='abuse', actor='T1',
         sql="delete from public.courses where id = '{C2}'",
         expect='none', check="UNCHANGED(courses)"),
    dict(id='IN-18', claim='C4', kind='abuse', actor='R',
         sql="insert into storage.objects (bucket_id, name, metadata) values "
             "('assignment-files', '{AR}/brief.pdf', '{{\"size\":1}}')",
         expect='error', check="(select count(*) = 0 from storage.objects where bucket_id = 'assignment-files')"),

    # ---- C6: the anonymous (logged-out) API key gets nothing -----------------------------------------
    dict(id='AN-01', claim='C6', kind='abuse', actor='anon', sql="select * from public.profiles", expect='none'),
    dict(id='AN-02', claim='C6', kind='abuse', actor='anon', sql="select * from public.courses", expect='none'),
    dict(id='AN-03', claim='C6', kind='abuse', actor='anon', sql="select * from public.grades", expect='none'),
    dict(id='AN-04', claim='C6', kind='abuse', actor='anon',
         sql="select public.enroll_by_code('CODEC1AA')", expect='error', check="UNCHANGED(enrollments)"),
    dict(id='AN-05', claim='C6', kind='abuse', actor='anon', sql="select * from storage.objects", expect='none'),
    dict(id='AN-06', claim='C6', kind='abuse', actor='anon', sql="select public.admin_stats()", expect='error'),
    dict(id='AN-07', claim='C6', kind='abuse', actor='anon',
         sql="insert into public.courses (instructor_id, name, course_code) values ('{T1}', 'anon', 'AN1')",
         expect='error', check="UNCHANGED(courses)"),
]
