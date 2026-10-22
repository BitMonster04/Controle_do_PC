// Cliente do backend no Pi. Credenciais ficam em cookie HttpOnly, nunca no JS.
export function createClient() {
  let listener=()=>{};
  async function request(path,body) {
    try {
      const response=await fetch('./api/'+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
      const data=await response.json();
      if(!response.ok) return {data:null,error:new Error(data.message||'Falha de comunicacao com o Pi.')};
      return {data,error:null};
    }catch(e){return {data:null,error:new Error('Nao foi possivel conectar ao Pi.')}}
  }
  return {
    auth:{
      onAuthStateChange(fn){listener=fn;},
      async enroll(code){const r=await request('enroll',{code});if(!r.error)listener('SIGNED_IN',r.data.session);return r;},
      async getSession(){const r=await request('session');return {data:{session:r.data?.session||null},error:r.error};},
      async signInWithPassword(values){const r=await request('login',{password:values.password});if(!r.error)listener('SIGNED_IN',r.data.session);return r;},
      async signOut(){const r=await request('logout',{});if(!r.error)listener('SIGNED_OUT',null);return r;}
    },
    rpc(name,body){return request('rpc/'+name,body);}
  };
}
