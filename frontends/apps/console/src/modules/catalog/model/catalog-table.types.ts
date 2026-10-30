import type { CatalogListItem, CatalogItem } from "./catalog.types";

export interface CatalogQuickEditTarget {
  item: CatalogItem;
  rootId: string | null;
  shared: boolean;
}

export type CatalogQuickEditSection = "price" | "stock";
export interface CatalogQuickEditSelection {
  id: string;
  rootId: string | null;
  section: CatalogQuickEditSection;
}
export interface ExpandedCatalogVariants {
  items: readonly CatalogListItem[];
  loading: boolean;
  fetching: boolean;
  error: string;
  total: number;
  offset: number;
  limit: number;
}
export type CatalogVariantExpansions = Readonly<
  Record<string, ExpandedCatalogVariants>
>;
