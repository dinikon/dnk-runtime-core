export interface CreateItemPackagingRequestDTO {
  packaging_type_id: string;
  code: string;
  name: string;
  content_quantity: string;
  content_uom: string;
}
export interface CreateItemPackagingResponseDTO {
  id: string;
  inventory_item_id: string;
  packaging_type_id: string;
  code: string;
  name: string;
  content_quantity: string;
  content_uom: string;
}
export interface GetItemPackagingResponseDTO {
  id: string;
  inventory_item_id: string;
  packaging_type_id: string;
  code: string;
  name: string;
  content_quantity: string;
  content_uom: string;
}
export interface PatchItemPackagingRequestDTO {
  packaging_type_id?: string;
  code?: string;
  name?: string;
  content_quantity?: string;
  content_uom?: string;
}
export interface PatchItemPackagingResponseDTO {
  id: string;
  inventory_item_id: string;
  packaging_type_id: string;
  code: string;
  name: string;
  content_quantity: string;
  content_uom: string;
}
export interface ItemPackagingListItemDTO {
  id: string;
  inventory_item_id: string;
  packaging_type_id: string;
  code: string;
  name: string;
  content_quantity: string;
  content_uom: string;
}
export interface ListItemPackagingsResponseDTO {
  items: ItemPackagingListItemDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface ListItemPackagingsRequestDTO {
  search?: string;
  offset: number;
  limit: number;
}
