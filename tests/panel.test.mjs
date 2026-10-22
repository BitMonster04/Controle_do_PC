import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync(new URL('../app.js',import.meta.url),'utf8').replace("const {createClient} = await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.57.4/+esm');",'');
function panel(status,options={}) {
  const elements=new Map(); const listeners=new Map(); let commandCalls=[];
  const get=id=>{
    if(!elements.has(id)) elements.set(id,{hidden:false,textContent:'',className:'',disabled:false,value:'',setAttribute(){},addEventListener(event,fn){listeners.set(id+':'+event,fn);}});
    return elements.get(id);
  };
  const client={auth:{onAuthStateChange(){},getSession:async()=>({data:{session:{user:{id:'chief'}}}}),signOut:async()=>({})},rpc:async(name,args)=>{
    if(name==='pc_command'){commandCalls.push(args);return {data:1,error:options.commandError||null};}
    return options.apiError?{error:new Error('Sem conexao')}:{data:status};
  }};
  const ctx=vm.createContext({window:{PC_CONFIG:{supabaseUrl:'https://example.supabase.co',supabasePublicKey:'sb_publishable_test',deviceId:'pc-jogos'}},document:{getElementById:get},createClient:()=>client,setInterval(){},setTimeout(){},console});
  return {ctx,get,listeners,commandCalls,ready:vm.runInContext('(async()=>{'+source+'})()',ctx)};
}
test('trava ativa confirmada: vermelho e clique para desativar',async()=>{const p=panel({online:true,blocked:true,pending:false});await p.ready;assert.equal(p.get('toggle-label').textContent,'Trava ativada');assert.match(p.get('toggle').className,/active/);assert.equal(p.get('toggle').disabled,false);await p.listeners.get('toggle:click')();assert.equal(p.commandCalls[0].p_blocked,false);});
test('trava desativada confirmada: verde e clique para ativar',async()=>{const p=panel({online:true,blocked:false,pending:false});await p.ready;assert.equal(p.get('toggle-label').textContent,'Trava desativada');assert.match(p.get('toggle').className,/inactive/);await p.listeners.get('toggle:click')();assert.equal(p.commandCalls[0].p_blocked,true);});
test('offline conserva ultimo estado e impede envio',async()=>{const p=panel({online:false,blocked:true,last_seen:'2026-10-22T12:00:00Z'});await p.ready;assert.equal(p.get('toggle').disabled,true);assert.equal(p.get('connection-text').textContent,'Computador offline');await p.listeners.get('toggle:click')();assert.equal(p.commandCalls.length,0);});
test('ordem pendente nao confirma o novo estado',async()=>{const p=panel({online:true,blocked:false,pending:true});await p.ready;assert.equal(p.get('toggle-label').textContent,'Aplicando…');assert.equal(p.get('toggle').disabled,true);});
test('sem estado inicial nao permite comando',async()=>{const p=panel({online:true,blocked:null,pending:false});await p.ready;assert.equal(p.get('toggle').disabled,true);await p.listeners.get('toggle:click')();assert.equal(p.commandCalls.length,0);});
test('erro de API bloqueia comando e mostra falha',async()=>{const p=panel(null,{apiError:true});await p.ready;assert.equal(p.get('toggle').disabled,true);assert.match(p.get('panel-error').textContent,/conexao/);});
test('ordem rejeitada mantem estado e mostra erro',async()=>{const p=panel({online:true,blocked:true,pending:false},{commandError:new Error('Sem permissao')});await p.ready;await p.listeners.get('toggle:click')();assert.equal(p.get('toggle-label').textContent,'Trava ativada');assert.equal(p.get('panel-error').textContent,'Sem permissao');});
