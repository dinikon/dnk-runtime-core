import type {
  PackagingType,
  PackagingTypeCreateValues,
  PackagingTypeChanges,
  PackagingTypesListParams,
  PackagingTypesPage,
} from "../model/packaging-type.types.ts";
import type {
  CreatePackagingTypeRequestDTO,
  CreatePackagingTypeResponseDTO,
  GetPackagingTypeResponseDTO,
  PatchPackagingTypeRequestDTO,
  PatchPackagingTypeResponseDTO,
  PackagingTypeListItemDTO,
  ListPackagingTypesRequestDTO,
  ListPackagingTypesResponseDTO,
} from "./packaging-type.dto.ts";

export function packagingTypeFromDto(
  dto:
    | CreatePackagingTypeResponseDTO
    | GetPackagingTypeResponseDTO
    | PatchPackagingTypeResponseDTO
    | PackagingTypeListItemDTO,
): PackagingType {
  return {
    id: dto.id,
    code: dto.code,
    name: dto.name,
    isActive: dto.is_active,
  };
}
export function packagingTypesPageFromDto(
  dto: ListPackagingTypesResponseDTO,
): PackagingTypesPage {
  return {
    items: dto.items.map(packagingTypeFromDto),
    total: dto.total,
    offset: dto.offset,
    limit: dto.limit,
  };
}
export function packagingTypeCreateToDto(
  values: PackagingTypeCreateValues,
): CreatePackagingTypeRequestDTO {
  return { code: values.code, name: values.name };
}
export function packagingTypePatchToDto(
  values: PackagingTypeChanges,
): PatchPackagingTypeRequestDTO {
  const dto: PatchPackagingTypeRequestDTO = {};
  if (values.code !== undefined) dto.code = values.code;
  if (values.name !== undefined) dto.name = values.name;
  if (values.isActive !== undefined) dto.is_active = values.isActive;
  return dto;
}
export function packagingTypesParamsToDto(
  params: PackagingTypesListParams,
): ListPackagingTypesRequestDTO {
  return {
    offset: params.offset,
    limit: params.limit,
    ...(params.search ? { search: params.search } : {}),
    ...(params.isActive !== null ? { is_active: params.isActive } : {}),
  };
}
