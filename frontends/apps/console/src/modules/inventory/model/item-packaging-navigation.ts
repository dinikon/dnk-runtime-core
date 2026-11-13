import type {RouteLocationRaw} from "vue-router";
const safePath=(value:unknown):value is string=>typeof value==="string"&&!/[\\\u0000-\u001f]/.test(value);
export function itemPackagingsLocation(inventoryItemId:string,returnTo:string):RouteLocationRaw{return {name:"inventory-item-packagings",params:{inventoryItemId},query:{returnTo}};}
export function itemPackagingEditLocation(inventoryItemId:string,packagingId:string,returnTo:string):RouteLocationRaw{return {name:"inventory-item-packaging-edit",params:{inventoryItemId,packagingId},query:{returnTo}};}
export function itemPackagingsReturnPath(itemId:string,value:unknown):string{
 if(safePath(value)){
  const path=value.split(/[?#]/,1)[0];
  if(path==="/inventory/items"||path===`/inventory/items/${encodeURIComponent(itemId)}`)return value;
 }
 return `/inventory/items/${encodeURIComponent(itemId)}`;
}
export function itemPackagingReturnPath(itemId:string,value:unknown):string{
 const fallback=`/inventory/items/${encodeURIComponent(itemId)}/packagings`;
 return safePath(value)&&value.split(/[?#]/,1)[0]===fallback?value:fallback;
}
