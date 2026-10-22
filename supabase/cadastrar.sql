-- 1. Crie o usuario do chefe em Authentication > Users > Add user.
-- 2. Substitua o email abaixo e execute no SQL Editor.
-- Nao cole a senha do Windows aqui. Este login e exclusivo do painel.
insert into pc_private.operators(user_id)
select id from auth.users where lower(email)=lower('EMAIL_DO_CHEFE_AQUI')
on conflict do nothing;

-- 3. Execute UMA VEZ o bloco abaixo e guarde o token retornado.
-- Ele so sera usado pelo instalador NA REMOTA; nunca publique no GitHub.
-- pgcrypto nao e necessario: UUIDs aleatorios combinados fornecem > 240 bits.
do $$ begin
  if exists(select 1 from pc_private.devices where id='pc-jogos') then
    raise exception 'Dispositivo ja cadastrado. Nao sobrescreva o token existente.';
  end if;
end $$;
with segredo as (
  select replace(gen_random_uuid()::text||gen_random_uuid()::text,'-','') as token
), cadastro as (
  insert into pc_private.devices(id,name,token_hash)
  select 'pc-jogos','Computador dos jogos',encode(sha256(convert_to(token,'UTF8')),'hex')
  from segredo returning id
)
select cadastro.id,segredo.token as token_somente_para_a_remota from cadastro cross join segredo;
