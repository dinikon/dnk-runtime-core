export interface CategoryRowDTO {
  id: string;
  parent_id: string | null;
  source_locale: string;
  source_name: string;
  name: string | null;
  is_default: boolean;
}
