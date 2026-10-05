export interface SkuDto {
  id: string;
  code: string;
  title: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
}
export interface CreateSkuDto {
  code: string;
  title: string;
}
