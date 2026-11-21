import type { CatalogItemsParams } from "./catalog-list-state";

export const catalogListKeys = {
  variants: (
    tenant: string,
    session: string,
    rootId: string,
    locale: string,
    pagination: { offset: number; limit: number },
  ): readonly unknown[] => [
    "catalog",
    tenant,
    session,
    "variants",
    rootId,
    locale,
    pagination,
  ],
  quickEdit: (
    tenant: string,
    session: string,
    locale: string,
    id: string,
    rootId: string | null,
    section: string,
  ): readonly unknown[] => [
    "catalog",
    tenant,
    session,
    "quick-edit",
    locale,
    rootId,
    id,
    section,
  ],
  all: (tenant: string, session: string): readonly string[] => [
    "catalog",
    tenant,
    session,
  ],
  list: (
    tenant: string,
    session: string,
    locale: string,
    params: CatalogItemsParams,
  ): readonly unknown[] => [
    ...catalogListKeys.all(tenant, session),
    "list-items",
    locale,
    params,
  ],
};
