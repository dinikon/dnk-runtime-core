export interface PackagingType {
  id: string;
  code: string;
  name: string;
  isActive: boolean;
}
export interface PackagingTypeCreateValues {
  code: string;
  name: string;
}
export interface PackagingTypeEditValues extends PackagingTypeCreateValues {
  isActive: boolean;
}
export type PackagingTypeChanges = Partial<PackagingTypeEditValues>;
export type PackagingTypeFieldErrors = Partial<
  Record<keyof PackagingTypeEditValues, string>
>;
export type PackagingTypeActivity = "all" | "active" | "inactive";
export interface PackagingTypesListParams {
  search: string;
  isActive: boolean | null;
  offset: number;
  limit: number;
}
export interface PackagingTypesPageParams {
  search: string;
  activity: PackagingTypeActivity;
  page: number;
  limit: number;
}
export interface PackagingTypesPage {
  items: PackagingType[];
  total: number;
  offset: number;
  limit: number;
}
