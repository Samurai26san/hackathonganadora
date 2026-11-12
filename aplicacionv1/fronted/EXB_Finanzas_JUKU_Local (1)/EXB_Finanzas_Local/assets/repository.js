/* Local data boundary. Financial records are always loaded from the supplied Excel
   extraction; old synthetic localStorage data is deliberately never reused.
   Demo roles are interface behavior, not production authentication. */
window.ExbRepository=(()=>{
 const key='exb-excel-a6670453-v3';let saved;try{saved=JSON.parse(localStorage.getItem(key)||'null')}catch(e){}
 const state={version:3,users:saved?.version===3?saved.users:[{email:'tecnico@exb.demo',name:'Equipo técnico',role:'Técnico',active:true},{email:'admin@exb.demo',name:'Administración',role:'Administrador',active:true}],audit:saved?.version===3?saved.audit:[]};
 let data=structuredClone(EXB_SEED);
 function persist(){try{localStorage.setItem(key,JSON.stringify(state));return true}catch(e){return false}}
 function log(user,action){state.audit.unshift({at:new Date().toISOString(),user,action});state.audit=state.audit.slice(0,300);persist()}
 return {data:()=>data,users:()=>state.users,audit:()=>state.audit,
 authenticate(email,password){return password==='Demo2026!'?state.users.find(u=>u.email.toLowerCase()===email.toLowerCase().trim()&&u.active)||null:null},
 log,changeRole(actor,email,role){if(actor.role!=='Administrador')throw Error('Acceso no autorizado');if(actor.email===email)throw Error('No puedes cambiar tu propio rol');if(!['Técnico','Administrador'].includes(role))throw Error('Rol inválido');const u=state.users.find(u=>u.email===email);if(!u)throw Error('Cuenta inexistente');u.role=role;log(actor.email,'Cambió rol de '+email+' a '+role)},
 reset(actor){if(actor.role!=='Administrador')throw Error('Acceso no autorizado');data=structuredClone(EXB_SEED);log(actor.email,'Recargó los datos originales del Excel')}
 };
})();
