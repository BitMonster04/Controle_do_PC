let installEvent;
const button=document.getElementById('install-app');
const help=document.getElementById('install-help');
const installed=()=>window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;
if(installed()) button.hidden=true;
window.addEventListener('beforeinstallprompt',event=>{
  event.preventDefault();installEvent=event;button.hidden=false;
});
window.addEventListener('appinstalled',()=>{button.hidden=true;help.hidden=true;installEvent=null;});
button.addEventListener('click',async()=>{
  if(installEvent){const event=installEvent;installEvent=null;await event.prompt();const choice=await event.userChoice;if(choice.outcome==='accepted')button.hidden=true;}
  else help.hidden=false;
});
if('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js',{scope:'./'}).catch(()=>{});
