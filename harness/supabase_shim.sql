-- Minimal local stand-in for the parts of Supabase that target/app-under-test/supabase/schema.sql uses.
-- It is NOT Supabase. It reproduces only what the schema's security depends on:
--   * roles anon / authenticated / service_role (created once per cluster by harness/db.py)
--   * auth.users + auth.uid() reading the JWT subject the way PostgREST exposes it
--   * Supabase's default privileges (tables/functions in public granted to anon + authenticated)
--   * storage.buckets / storage.objects (RLS on) and storage.foldername()
-- PostgREST runs every API request as: BEGIN; SET LOCAL ROLE <jwt role>; set request.jwt.claims; <query>; COMMIT.
-- harness/run_study.py does the same, which is why the study works at the SQL level.

create schema if not exists auth;
create schema if not exists storage;

grant usage on schema public, auth, storage to anon, authenticated, service_role;

-- Supabase default privileges: everything new in public is granted to the API roles; RLS then restricts it.
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
alter default privileges in schema public grant all on sequences to anon, authenticated, service_role;
alter default privileges in schema public grant execute on functions to anon, authenticated, service_role;

create table auth.users (
  id uuid primary key,
  email text,
  raw_user_meta_data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create or replace function auth.uid() returns uuid language sql stable as $$
  select coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
  )::uuid
$$;
grant execute on function auth.uid() to anon, authenticated, service_role;

create table storage.buckets (
  id text primary key,
  name text not null,
  public boolean default false,
  file_size_limit bigint
);

create table storage.objects (
  id uuid primary key default gen_random_uuid(),
  bucket_id text references storage.buckets(id),
  name text not null,
  owner uuid,
  metadata jsonb,
  created_at timestamptz not null default now(),
  unique (bucket_id, name)
);
alter table storage.objects enable row level security;
grant select, insert, update, delete on storage.objects to anon, authenticated, service_role;
grant select on storage.buckets to anon, authenticated, service_role;

-- Same behaviour as Supabase's storage.foldername(): the path's folder parts, without the file name.
create or replace function storage.foldername(name text) returns text[] language plpgsql immutable as $$
declare
  _parts text[];
begin
  _parts := string_to_array(name, '/');
  return _parts[1:array_length(_parts, 1) - 1];
end $$;
grant execute on function storage.foldername(text) to anon, authenticated, service_role;
