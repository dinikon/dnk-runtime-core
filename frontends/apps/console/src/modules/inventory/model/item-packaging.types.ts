import type { PackagingType } from "./packaging-type.types.ts";
export interface ItemPackagingValues {
 packagingTypeId: string; code: string; name: string; contentQuantity: string; contentUom: string;
}
export interface ItemPackaging extends ItemPackagingValues { id: string; inventoryItemId: string; }
export type ItemPackagingChanges = Partial<ItemPackagingValues>;
export type ItemPackagingErrors = Partial<Record<keyof ItemPackagingValues, string>>;
export interface ItemPackagingsListParams {search: string; offset: number; limit: number;}
export interface ItemPackagingsPageParams {search: string; page: number; limit: number;}
export interface ItemPackagingsPage { items: ItemPackaging[]; total: number; offset: number; limit: number; }
export interface PackagingTypePickerState {
 search: string; options: readonly PackagingType[]; total: number;
 loading: boolean; fetchingMore: boolean; hasMore: boolean; error: string;
 selected?: PackagingType; selectedLoading: boolean; selectedError: string;
}
