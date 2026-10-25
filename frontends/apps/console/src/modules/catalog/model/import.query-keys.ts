export const importKeys = {
  all: (tenant: string, session: string): readonly string[] => [
    "catalog-imports",
    tenant,
    session,
  ],
  list: (
    tenant: string,
    session: string,
    page: number,
  ): readonly (string | number)[] => [
    ...importKeys.all(tenant, session),
    "list",
    page,
  ],
  detail: (tenant: string, session: string, id: string): readonly string[] => [
    ...importKeys.all(tenant, session),
    "detail",
    id,
  ],
  rows: (
    tenant: string,
    session: string,
    id: string,
    page: number,
    outcome: string,
  ): readonly (string | number)[] => [
    ...importKeys.all(tenant, session),
    "rows",
    id,
    page,
    outcome,
  ],
};
