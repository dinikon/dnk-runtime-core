import type { CatalogItemsParams } from "./catalog-list-state";

export const catalogListKeys = {
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
