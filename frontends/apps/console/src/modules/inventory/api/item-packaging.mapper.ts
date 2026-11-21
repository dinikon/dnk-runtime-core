import type {
  ItemPackaging,
  ItemPackagingValues,
  ItemPackagingChanges,
  ItemPackagingsListParams,
  ItemPackagingsPage,
} from "../model/item-packaging.types.ts";
import type {
  CreateItemPackagingRequestDTO,
  CreateItemPackagingResponseDTO,
  GetItemPackagingResponseDTO,
  PatchItemPackagingRequestDTO,
  PatchItemPackagingResponseDTO,
  ItemPackagingListItemDTO,
  ListItemPackagingsResponseDTO,
  ListItemPackagingsRequestDTO,
} from "./item-packaging.dto.ts";
export function itemPackagingFromDto(
  dto:
    | CreateItemPackagingResponseDTO
    | GetItemPackagingResponseDTO
    | PatchItemPackagingResponseDTO
    | ItemPackagingListItemDTO,
): ItemPackaging {
  return {
    id: dto.id,
    inventoryItemId: dto.inventory_item_id,
    packagingTypeId: dto.packaging_type_id,
    code: dto.code,
    name: dto.name,
    contentQuantity: dto.content_quantity,
    contentUom: dto.content_uom,
  };
}
export function itemPackagingCreateToDto(
  value: ItemPackagingValues,
): CreateItemPackagingRequestDTO {
  return {
    packaging_type_id: value.packagingTypeId,
    code: value.code,
    name: value.name,
    content_quantity: value.contentQuantity,
    content_uom: value.contentUom,
  };
}
export function itemPackagingPatchToDto(
  value: ItemPackagingChanges,
): PatchItemPackagingRequestDTO {
  const dto: PatchItemPackagingRequestDTO = {};
  if (value.packagingTypeId !== undefined)
    dto.packaging_type_id = value.packagingTypeId;
  if (value.code !== undefined) dto.code = value.code;
  if (value.name !== undefined) dto.name = value.name;
  if (value.contentQuantity !== undefined)
    dto.content_quantity = value.contentQuantity;
  if (value.contentUom !== undefined) dto.content_uom = value.contentUom;
  return dto;
}
export function itemPackagingsParamsToDto(
  params: ItemPackagingsListParams,
): ListItemPackagingsRequestDTO {
  return {
    search: params.search || undefined,
    offset: params.offset,
    limit: params.limit,
  };
}
export function itemPackagingsPageFromDto(
  dto: ListItemPackagingsResponseDTO,
): ItemPackagingsPage {
  return {
    items: dto.items.map(itemPackagingFromDto),
    total: dto.total,
    offset: dto.offset,
    limit: dto.limit,
  };
}
