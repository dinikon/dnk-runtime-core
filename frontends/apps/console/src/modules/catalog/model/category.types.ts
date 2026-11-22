export interface CatalogCategory {
  id: string;
  parentId: string | null;
  sourceLocale: string;
  sourceName: string;
  name: string | null;
  isDefault: boolean;
}
export interface CategoryOption extends CatalogCategory {
  path: string;
  depth: number;
}
export interface CategorySelection {
  primary_category_id: string;
  additional_category_ids: string[];
}
export type CategoryChange =
  | { action: "create"; locale: string; name: string; parent: string | null }
  | {
      action: "update";
      id: string;
      translations?: Record<string, string>;
      parent?: string | null;
    }
  | { action: "delete" | "default"; id: string };
