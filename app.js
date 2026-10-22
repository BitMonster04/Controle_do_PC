const $ = id => document.getElementById(id);
const cfg = window.PC_CONFIG || {};
let client, session, last, polling = false, submitting = false, apiFailed = true;
function view(name) {
  for (const id of ['setup','login','panel']) $(id).hidden = id !== name;
  $('logout').hidden = name !== 'panel';
  if (cfg.pi && name === 'login') {
    $('login').hidden = true; $('panel').hidden = false; render();
  }
}
function render() {
  if (cfg.pi && !session) {
    $('toggle').className = 'toggle unknown'; $('toggle').disabled = false;
    $('toggle-label').textContent = 'Entrar no controle';
    $('toggle-action').textContent = 'Clique para acessar';
    $('connection').className = 'connection'; $('connection-text').textContent = 'Acesso protegido';
    $('hint').textContent = 'Entre para ver se o computador está online e controlar a trava.';
    $('last-seen').textContent = ''; $('panel-error').textContent = ''; return;
  }
  const online = !apiFailed && last?.online === true;
  const pending = last?.pending === true || submitting;
  const known = typeof last?.blocked === 'boolean';
  $('connection').className = 'connection' + (online ? ' online' : '');
  $('connection-text').textContent = apiFailed ? 'Sem conexão com o painel' : online ? 'Computador online' : last?.last_seen ? 'Computador offline' : 'Aguardando primeira conexão';
  $('toggle').className = 'toggle ' + (known ? last.blocked ? 'active' : 'inactive' : 'unknown') + (!online ? ' offline' : '') + (pending ? ' pending' : '');
  $('toggle').disabled = !online || pending || !known;
  $('toggle-label').textContent = pending ? 'Aplicando…' : known ? last.blocked ? 'Trava ativada' : 'Trava desativada' : 'Aguardando estado';
  $('toggle-action').textContent = !online ? 'Aguardando o computador' : pending ? 'Esperando confirmação' : known ? last.blocked ? 'Clique para desativar' : 'Clique para ativar' : 'Aguardando o agente';
  $('lock-shackle').setAttribute('d', known && !last.blocked ? 'M15 23v-7a9 9 0 0 1 17-4' : 'M15 23v-7a9 9 0 0 1 18 0v7');
  $('hint').textContent = !online ? 'A trava não pode ser alterada enquanto a máquina estiver sem comunicação.' : pending ? 'A ordem foi enviada. Aguarde a confirmação da REMOTA.' : known ? last.blocked ? 'Os jogos identificados estão com acesso à internet bloqueado.' : 'O acesso à internet dos jogos está liberado.' : 'A máquina ainda não informou o estado da trava.';
  $('last-seen').textContent = last?.last_seen ? 'Último contato: ' + new Date(last.last_seen).toLocaleString('pt-BR') + (last.rule_count != null ? ' · ' + last.rule_count + ' regras' : '') : '';
  $('device-name').textContent = last?.name || 'Computador dos jogos';
}
async function refresh() {
  if (!session || polling) return;
  polling = true;
  try {
    const {data,error} = await client.rpc('pc_status', {p_device:cfg.deviceId});
    if (error) throw error;
    last = data; apiFailed = false;
    $('panel-error').textContent = data.last_error || '';
  } catch (e) { apiFailed = true; $('panel-error').textContent = e.message || 'Não foi possível consultar a máquina.'; }
  finally { polling = false; render(); }
}
if (!cfg.pi && (!cfg.supabaseUrl || !cfg.supabasePublicKey)) { view('setup'); }
else {
  if (cfg.pi) {
    const local = await import('./api.js');
    client = local.createClient();
    $('email').required = false;
    $('email').hidden = true;
    document.querySelector('label[for="email"]').hidden = true;
  } else {
    const {createClient} = await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.57.4/+esm');
    if (cfg.supabasePublicKey.startsWith('sb_secret_')) throw new Error('Use somente uma chave pública.');
    client = createClient(cfg.supabaseUrl, cfg.supabasePublicKey, {auth:{persistSession:true,autoRefreshToken:true}});
  }
  client.auth.onAuthStateChange((_event,s) => { session=s; view(s?'panel':'login'); if(s) setTimeout(refresh,0); });
  const result = await client.auth.getSession(); session=result.data.session; view(session?'panel':'login');
  if(session) await refresh();
  setInterval(refresh,5000);
}
$('login-form').addEventListener('submit',async e => {
  e.preventDefault(); const b=e.target.querySelector('button'); b.disabled=true; $('login-error').textContent='';
  try { const {error}=await client.auth.signInWithPassword({email:$('email').value.trim(),password:$('password').value}); if(error) throw error; $('password').value=''; }
  catch(e){$('login-error').textContent=e.message;} finally{b.disabled=false;}
});
$('logout').addEventListener('click',async()=>{await client.auth.signOut();last=null;apiFailed=true;render();});
$('close-login').addEventListener('click',()=>{if(cfg.pi){$('login').hidden=true;$('toggle').focus();}});
$('toggle').addEventListener('click',async()=>{
  if (cfg.pi && !session) { $('login').hidden = false; $('password').focus(); return; }
  if(submitting || !last?.online || apiFailed || last.pending || typeof last.blocked!=='boolean') return;
  submitting=true;render();$('panel-error').textContent='';
  try {const {error}=await client.rpc('pc_command',{p_device:cfg.deviceId,p_blocked:!last.blocked});if(error) throw error;await refresh();}
  catch(e){$('panel-error').textContent=e.message;}finally{submitting=false;render();}
});
