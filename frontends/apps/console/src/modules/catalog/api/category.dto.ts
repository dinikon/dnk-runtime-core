export interface CategoryRowDTO {
  id: string;
  parent_id: string | null;
  fallback_locale: string;
  fallback_name: string;
  name: string | null;
  is_default: boolean;
}
