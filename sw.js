// Nenhum estado do computador, cookie, token ou resposta da API e armazenado.
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('fetch',event=>{
  if(event.request.mode==='navigate') event.respondWith(fetch(event.request).catch(()=>new Response(
    '<!doctype html><html lang="pt-BR"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Controle PC Giovanni</title><body style="background:#10141b;color:white;text-align:center;padding:60px 20px;font:18px system-ui"><h1>Sem conexão</h1><p>Conecte o celular à internet e abra o painel novamente.</p><p>O estado da trava não foi alterado.</p></body></html>',
    {headers:{'Content-Type':'text/html; charset=utf-8'},status:503}
  )));
});
