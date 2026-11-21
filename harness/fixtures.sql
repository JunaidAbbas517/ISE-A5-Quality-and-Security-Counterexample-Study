-- Frozen synthetic fixture: a5-fixtures-v1. No real people; emails use the reserved .invalid domain.
-- Users are created by inserting into auth.users, which fires the app's own handle_new_user() trigger
-- (the same path Supabase Auth sign-up takes).
--
-- Actors
--   A  admin                      ...0a01
--   T1 active instructor, owns C1 ...0a11
--   T2 active instructor, owns C2 ...0a12
--   P  pending instructor         ...0a21  (never approved)
--   R  revoked instructor, owns CR...0a22  (approved, built a course, then set to 'rejected' by A)
--   S1 student in C1 and CR       ...0a31
--   S2 student in C2              ...0a32

insert into auth.users (id, email, raw_user_meta_data) values
  ('00000000-0000-0000-0000-000000000a01', 'admin@a5.invalid',  '{"full_name":"Admin A"}'),
  ('00000000-0000-0000-0000-000000000a11', 't1@a5.invalid',     '{"full_name":"Teacher One","requested_role":"instructor"}'),
  ('00000000-0000-0000-0000-000000000a12', 't2@a5.invalid',     '{"full_name":"Teacher Two","requested_role":"instructor"}'),
  ('00000000-0000-0000-0000-000000000a21', 'pending@a5.invalid','{"full_name":"Pending P","requested_role":"instructor"}'),
  ('00000000-0000-0000-0000-000000000a22', 'revoked@a5.invalid','{"full_name":"Revoked R","requested_role":"instructor"}'),
  ('00000000-0000-0000-0000-000000000a31', 's1@a5.invalid',     '{"full_name":"Student One"}'),
  ('00000000-0000-0000-0000-000000000a32', 's2@a5.invalid',     '{"full_name":"Student Two"}');

-- The first admin is created exactly as the app README says (SQL editor, superuser).
update public.profiles set role = 'admin', status = 'active' where id = '00000000-0000-0000-0000-000000000a01';

-- Admin approves T1, T2 and R through the app's own RPC.
begin;
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000a01', true);
set local role authenticated;
select public.set_instructor_status('00000000-0000-0000-0000-000000000a11', 'active');
select public.set_instructor_status('00000000-0000-0000-0000-000000000a12', 'active');
select public.set_instructor_status('00000000-0000-0000-0000-000000000a22', 'active');
commit;

insert into public.courses (id, instructor_id, name, course_code, enrollment_code, archived) values
  ('00000000-0000-0000-0000-0000000c0001', '00000000-0000-0000-0000-000000000a11', 'Software Testing',  'SE101', 'CODEC1AA', false),
  ('00000000-0000-0000-0000-0000000c0002', '00000000-0000-0000-0000-000000000a12', 'Databases',         'DB201', 'CODEC2BB', false),
  ('00000000-0000-0000-0000-0000000c00ff', '00000000-0000-0000-0000-000000000a22', 'Revoked Course',    'RV301', 'CODECRCC', false),
  ('00000000-0000-0000-0000-0000000c00aa', '00000000-0000-0000-0000-000000000a11', 'Old Archived',      'OLD100','CODECXDD', true);

insert into public.enrollments (student_id, course_id) values
  ('00000000-0000-0000-0000-000000000a31', '00000000-0000-0000-0000-0000000c0001'),
  ('00000000-0000-0000-0000-000000000a31', '00000000-0000-0000-0000-0000000c00ff'),
  ('00000000-0000-0000-0000-000000000a32', '00000000-0000-0000-0000-0000000c0002');

insert into public.assignments (id, course_id, title, current_deadline, submission_type, total_marks) values
  ('00000000-0000-0000-0000-0000000a0001', '00000000-0000-0000-0000-0000000c0001', 'Unit test lab',   date_trunc('second', now()) + interval '7 days', 'file', 100),
  ('00000000-0000-0000-0000-0000000a0002', '00000000-0000-0000-0000-0000000c0001', 'Reading link',    date_trunc('second', now()) + interval '9 days', 'link', 20),
  ('00000000-0000-0000-0000-0000000a0003', '00000000-0000-0000-0000-0000000c0002', 'ER diagram',      date_trunc('second', now()) + interval '7 days', 'file', 100),
  ('00000000-0000-0000-0000-0000000a00ff', '00000000-0000-0000-0000-0000000c00ff', 'Revoked homework',date_trunc('second', now()) + interval '7 days', 'file', 100);

insert into storage.objects (bucket_id, name, owner, metadata) values
  ('submissions', '00000000-0000-0000-0000-0000000a0001/00000000-0000-0000-0000-000000000a31/u1/report.pdf', '00000000-0000-0000-0000-000000000a31', '{"size":1000}'),
  ('submissions', '00000000-0000-0000-0000-0000000a0003/00000000-0000-0000-0000-000000000a32/u2/er.pdf',     '00000000-0000-0000-0000-000000000a32', '{"size":2000}'),
  ('submissions', '00000000-0000-0000-0000-0000000a00ff/00000000-0000-0000-0000-000000000a31/u3/hw.pdf',     '00000000-0000-0000-0000-000000000a31', '{"size":3000}');

insert into public.submissions (id, assignment_id, student_id, attempt, summary, is_late) values
  ('00000000-0000-0000-0000-00000005b001', '00000000-0000-0000-0000-0000000a0001', '00000000-0000-0000-0000-000000000a31', 1, 'S1 lab', false),
  ('00000000-0000-0000-0000-00000005b002', '00000000-0000-0000-0000-0000000a0003', '00000000-0000-0000-0000-000000000a32', 1, 'S2 ER',  false),
  ('00000000-0000-0000-0000-00000005b0ff', '00000000-0000-0000-0000-0000000a00ff', '00000000-0000-0000-0000-000000000a31', 1, 'S1 hw',  false);

-- G1: saved but NOT returned (student must not see it). G2: returned (student may see it).
insert into public.grades (id, assignment_id, student_id, submission_id, marks, feedback, graded_by, returned_at) values
  ('00000000-0000-0000-0000-0000000d0001', '00000000-0000-0000-0000-0000000a0001', '00000000-0000-0000-0000-000000000a31',
   '00000000-0000-0000-0000-00000005b001', 55, 'draft', '00000000-0000-0000-0000-000000000a11', null),
  ('00000000-0000-0000-0000-0000000d0002', '00000000-0000-0000-0000-0000000a0002', '00000000-0000-0000-0000-000000000a31',
   null, 18, 'well done', '00000000-0000-0000-0000-000000000a11', now());

-- Admin revokes R after R's course already exists (the situation the claim "a rejected instructor can manage nothing" covers).
begin;
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000a01', true);
set local role authenticated;
select public.set_instructor_status('00000000-0000-0000-0000-000000000a22', 'rejected');
commit;
