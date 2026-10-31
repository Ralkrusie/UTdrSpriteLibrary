let database;
async function db(){
 if(!database)database=new Promise((resolve,reject)=>{const r=indexedDB.open('utdr-mobile',1);r.onupgradeneeded=()=>{r.result.createObjectStore('packs',{keyPath:'id'});r.result.createObjectStore('settings')};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
 return database;
}
export async function storage(store,method,...args){
 const database=await db();return new Promise((resolve,reject)=>{const tx=database.transaction(store,method==='get'||method==='getAll'?'readonly':'readwrite'),r=tx.objectStore(store)[method](...args);tx.oncomplete=()=>resolve(r.result);tx.onabort=tx.onerror=()=>reject(tx.error||r.error||Error('本地存储失败'))});
}
