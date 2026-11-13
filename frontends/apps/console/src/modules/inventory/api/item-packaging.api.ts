import {isAxiosError,isCancel} from "axios";
import {httpClient,getApiErrorMessage,getApiErrorStatus} from "@/app/providers/http";
import type {ItemPackaging,ItemPackagingValues,ItemPackagingChanges,ItemPackagingErrors,ItemPackagingsListParams,ItemPackagingsPage} from "../model/item-packaging.types";
import {ItemPackagingRequestError} from "../model/item-packaging.errors";
import type {CreateItemPackagingResponseDTO,GetItemPackagingResponseDTO,PatchItemPackagingResponseDTO,ListItemPackagingsResponseDTO} from "./item-packaging.dto";
import {itemPackagingFromDto,itemPackagingCreateToDto,itemPackagingPatchToDto,itemPackagingsParamsToDto,itemPackagingsPageFromDto} from "./item-packaging.mapper";
function requestError(cause: unknown,fallback: string): never {
 if(isCancel(cause))throw cause;
 const status=getApiErrorStatus(cause),fields:ItemPackagingErrors={};
 const detail:unknown=isAxiosError(cause)?cause.response?.data?.detail:undefined;
 if(status===422 && Array.isArray(detail))for(const issue of detail){
  if(typeof issue!=="object"||issue===null||!Array.isArray(issue.loc))continue;
  const field:unknown=issue.loc[1];
  if(field==="code"||field==="name")fields[field]="Проверьте значение поля.";
  if(field==="packaging_type_id")fields.packagingTypeId="Выберите тип тары.";
  if(field==="content_quantity")fields.contentQuantity="Укажите положительное конечное количество строкой.";
  if(field==="content_uom")fields.contentUom="Выберите единицу содержимого.";
 }
 throw new ItemPackagingRequestError(status===403?"Нет доступа к упаковкам товара.":status===404?"Товар или упаковка не найдены.":getApiErrorMessage(cause,fallback),status,fields);
}
function collection(itemId:string):string{return `/console/inventory/items/${encodeURIComponent(itemId)}/packagings`;}
export async function listItemPackagings(itemId:string,params:ItemPackagingsListParams,signal?:AbortSignal):Promise<ItemPackagingsPage>{try{
 const {data}=await httpClient.get<ListItemPackagingsResponseDTO>(collection(itemId),{params:itemPackagingsParamsToDto(params),signal});return itemPackagingsPageFromDto(data);
 }catch(error:unknown){return requestError(error,"Не удалось загрузить упаковки.");}}
export async function getItemPackaging(itemId:string,id:string,signal?:AbortSignal):Promise<ItemPackaging>{try{
 const {data}=await httpClient.get<GetItemPackagingResponseDTO>(`${collection(itemId)}/${encodeURIComponent(id)}`,{signal});return itemPackagingFromDto(data);
 }catch(error:unknown){return requestError(error,"Не удалось загрузить упаковку.");}}
export async function createItemPackaging(itemId:string,values:ItemPackagingValues,signal?:AbortSignal):Promise<ItemPackaging>{try{
 const {data}=await httpClient.post<CreateItemPackagingResponseDTO>(collection(itemId),itemPackagingCreateToDto(values),{signal});return itemPackagingFromDto(data);
 }catch(error:unknown){return requestError(error,"Не удалось создать упаковку.");}}
export async function patchItemPackaging(itemId:string,id:string,values:ItemPackagingChanges,signal?:AbortSignal):Promise<ItemPackaging>{try{
 const {data}=await httpClient.patch<PatchItemPackagingResponseDTO>(`${collection(itemId)}/${encodeURIComponent(id)}`,itemPackagingPatchToDto(values),{signal});return itemPackagingFromDto(data);
 }catch(error:unknown){return requestError(error,"Не удалось сохранить упаковку. Ваш ввод сохранён.");}}
