export interface CreatePackagingTypeRequestDTO {
  code: string;
  name: string;
}
export interface CreatePackagingTypeResponseDTO {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}
export interface GetPackagingTypeResponseDTO {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}
export interface PatchPackagingTypeRequestDTO {
  code?: string;
  name?: string;
  is_active?: boolean;
}
export interface PatchPackagingTypeResponseDTO {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}
export interface PackagingTypeListItemDTO {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}
export interface ListPackagingTypesResponseDTO {
  items: PackagingTypeListItemDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface ListPackagingTypesRequestDTO {
  search?: string;
  is_active?: boolean;
  offset: number;
  limit: number;
}
