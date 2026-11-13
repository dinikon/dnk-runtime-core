import type {ItemPackagingValues,ItemPackagingErrors} from "./item-packaging.types.ts";
import type {InventoryUom} from "./inventory-item-settings.types.ts";
export function positivePackagingQuantity(value:string):boolean{
 const match=/^\+?(\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.exec(value.trim());
 return !!match && /[1-9]/.test(match[1]!);
}
export function validateItemPackaging(value:ItemPackagingValues,uoms:readonly InventoryUom[]):ItemPackagingErrors{
 const errors:ItemPackagingErrors={};
 if(!value.packagingTypeId)errors.packagingTypeId="Выберите тип тары.";
 if(!value.code.trim())errors.code="Укажите код упаковки.";if(!value.name.trim())errors.name="Укажите название упаковки.";
 if(!positivePackagingQuantity(value.contentQuantity))errors.contentQuantity="Укажите положительное конечное количество, например 12 или 0.5.";
 if(!uoms.some(unit=>unit.code===value.contentUom))errors.contentUom="Выберите совместимую единицу содержимого.";
 return errors;
}
