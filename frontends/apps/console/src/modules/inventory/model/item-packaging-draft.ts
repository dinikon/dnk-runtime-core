import type {ItemPackagingValues,ItemPackagingChanges} from "./item-packaging.types.ts";
export function itemPackagingSnapshot(value:ItemPackagingValues):ItemPackagingValues{return {packagingTypeId:value.packagingTypeId,code:value.code,name:value.name,contentQuantity:value.contentQuantity,contentUom:value.contentUom};}
export function itemPackagingChanges(value:ItemPackagingValues,baseline:ItemPackagingValues):ItemPackagingChanges{
 const changes:ItemPackagingChanges={};
 if(value.packagingTypeId!==baseline.packagingTypeId)changes.packagingTypeId=value.packagingTypeId;
 if(value.code!==baseline.code)changes.code=value.code;if(value.name!==baseline.name)changes.name=value.name;
 if(value.contentQuantity!==baseline.contentQuantity)changes.contentQuantity=value.contentQuantity;
 if(value.contentUom!==baseline.contentUom)changes.contentUom=value.contentUom;return changes;
}
export class ItemPackagingDraft{
 values:ItemPackagingValues|null=null;private baseline:ItemPackagingValues|null=null;
 get changes():ItemPackagingChanges{return this.values&&this.baseline?itemPackagingChanges(this.values,this.baseline):{};}
 get dirty():boolean{return Object.keys(this.changes).length>0;}
 receive(value:ItemPackagingValues):void{if(!this.dirty)this.reset(value);}
 change(value:ItemPackagingValues):void{this.values=itemPackagingSnapshot(value);}
 reset(value:ItemPackagingValues):void{this.values=itemPackagingSnapshot(value);this.baseline=itemPackagingSnapshot(value);}
 clear():void{this.values=null;this.baseline=null;}
 acknowledge(sent:ItemPackagingValues,result:ItemPackagingValues):void{
  if(!this.values)return;const current=this.values;
  this.values={packagingTypeId:current.packagingTypeId===sent.packagingTypeId?result.packagingTypeId:current.packagingTypeId,
   code:current.code===sent.code?result.code:current.code,name:current.name===sent.name?result.name:current.name,
   contentQuantity:current.contentQuantity===sent.contentQuantity?result.contentQuantity:current.contentQuantity,
   contentUom:current.contentUom===sent.contentUom?result.contentUom:current.contentUom};this.baseline=itemPackagingSnapshot(result);
 }
}
