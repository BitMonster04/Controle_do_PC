-- Execute uma vez no SQL Editor do projeto Supabase dedicado ao painel.
begin;
create schema if not exists pc_private;
revoke all on schema pc_private from public, anon, authenticated;
create table pc_private.operators (
  user_id uuid primary key references auth.users(id) on delete cascade
);
create table pc_private.devices (
  id text primary key,
  name text not null,
  token_hash text not null,
  last_seen timestamptz,
  blocked boolean,
  rule_count integer,
  revision bigint not null default 0,
  ack_revision bigint not null default 0,
  desired boolean,
  expires_at timestamptz,
  last_error text,
  requested_by uuid references auth.users(id) on delete set null,
  requested_at timestamptz
);
create table pc_private.audit (
  id bigint generated always as identity primary key,
  device_id text not null references pc_private.devices(id),
  operator_id uuid references auth.users(id) on delete set null,
  blocked boolean not null,
  revision bigint not null,
  created_at timestamptz not null default now()
);
alter table pc_private.operators enable row level security;
alter table pc_private.devices enable row level security;
alter table pc_private.audit enable row level security;
revoke all on all tables in schema pc_private from public, anon, authenticated;

create function public.pc_status(p_device text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare d pc_private.devices;
begin
  if not exists (select 1 from pc_private.operators where user_id = auth.uid()) then
    raise exception 'Conta sem autorizacao para este painel.' using errcode = '42501';
  end if;
  select * into strict d from pc_private.devices where id = p_device;
  return jsonb_build_object('name',d.name,'last_seen',d.last_seen,
    'online',coalesce(d.last_seen > now()-interval '60 seconds',false),
    'blocked',d.blocked,'rule_count',d.rule_count,'revision',d.revision,
    'pending',d.revision>d.ack_revision and d.expires_at>now(),
    'last_error',case when d.revision>d.ack_revision and d.expires_at<=now()
      then 'A ordem expirou sem confirmacao. Tente novamente com a maquina online.' else d.last_error end);
end $$;

create function public.pc_command(p_device text,p_blocked boolean)
returns bigint language plpgsql security definer set search_path = '' as $$
declare d pc_private.devices;
begin
  if not exists (select 1 from pc_private.operators where user_id = auth.uid()) then
    raise exception 'Conta sem autorizacao.' using errcode = '42501';
  end if;
  if p_blocked is null then raise exception 'Estado invalido.'; end if;
  select * into strict d from pc_private.devices where id = p_device for update;
  if d.last_seen is null or d.last_seen < now()-interval '60 seconds' then
    raise exception 'Computador offline. Aguarde a reconexao.';
  end if;
  if d.revision>d.ack_revision and d.expires_at>now() then
    raise exception 'Ja existe uma ordem em andamento.';
  end if;
  update pc_private.devices set desired=p_blocked,revision=revision+1,
    expires_at=now()+interval '2 minutes',requested_by=auth.uid(),requested_at=now(),last_error=null
    where id=p_device returning * into d;
  insert into pc_private.audit(device_id,operator_id,blocked,revision)
    values(p_device,auth.uid(),p_blocked,d.revision);
  return d.revision;
end $$;

-- Unica funcao disponivel ao agente anonimo; exige segredo individual de 256 bits.
-- O agente nao recebe SQL, comandos de terminal nem caminhos fornecidos pela pagina.
create function public.pc_heartbeat(p_device text,p_token text,p_blocked boolean,
  p_rule_count integer,p_ack bigint default null,p_error text default null)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare d pc_private.devices;
begin
  select * into d from pc_private.devices where id=p_device for update;
  if not found or p_token is null or length(p_token)<40 or
    d.token_hash <> encode(sha256(convert_to(p_token,'UTF8')),'hex') then
    raise exception 'Credencial do agente invalida.' using errcode='42501';
  end if;
  if p_rule_count is null or p_rule_count<0 or p_blocked is null then
    raise exception 'Estado do firewall invalido.';
  end if;
  update pc_private.devices set last_seen=now(),blocked=p_blocked,rule_count=p_rule_count,
    ack_revision=case when p_ack=revision and
      (p_error is not null or p_blocked=desired) then revision else ack_revision end,
    last_error=case when p_ack=revision then left(p_error,500) else last_error end
    where id=p_device returning * into d;
  return jsonb_build_object('revision',d.revision,
    'action',case when d.revision>d.ack_revision and d.expires_at>now()
      then case when d.desired then 'bloquear' else 'desbloquear' end else null end);
end $$;

revoke all on function public.pc_status(text) from public,anon,authenticated;
revoke all on function public.pc_command(text,boolean) from public,anon,authenticated;
revoke all on function public.pc_heartbeat(text,text,boolean,integer,bigint,text) from public,anon,authenticated;
grant execute on function public.pc_status(text) to authenticated;
grant execute on function public.pc_command(text,boolean) to authenticated;
grant execute on function public.pc_heartbeat(text,text,boolean,integer,bigint,text) to anon;
commit;
