import type { SourcesParams } from "./supplier-source.types.ts";
export function sourcesParams(query: Record<string, unknown>): SourcesParams {
  const positive = (value: unknown, fallback: number): number =>
    typeof value === "string" &&
    /^\d+$/.test(value) &&
    Number.isSafeInteger(Number(value)) &&
    Number(value) > 0
      ? Number(value)
      : fallback;
  const limit = positive(query.limit, 20);
  const supplierModelKey =
    query.supplier_model_key === "crm.company" ||
    query.supplier_model_key === "crm.contact"
      ? query.supplier_model_key
      : "";
  return {
    supplierModelKey,
    search: typeof query.search === "string" ? query.search : "",
    supplierId:
      !!supplierModelKey &&
      typeof query.supplier === "string" &&
      /^[0-9a-f-]{36}$/i.test(query.supplier)
        ? query.supplier
        : "",
    activity:
      query.activity === "active" || query.activity === "inactive"
        ? query.activity
        : "all",
    fulfillmentMode:
      query.mode === "DROPSHIP" || query.mode === "PURCHASE_TO_WAREHOUSE"
        ? query.mode
        : "all",
    page: Math.min(positive(query.page, 1), 1000000),
    limit: [20, 50, 100].includes(limit) ? limit : 20,
  };
}
export function sourcesQuery(params: SourcesParams): Record<string, string> {
  return {
    ...(params.supplierModelKey
      ? { supplier_model_key: params.supplierModelKey }
      : {}),
    ...(params.search ? { search: params.search } : {}),
    ...(params.supplierId ? { supplier: params.supplierId } : {}),
    ...(params.activity !== "all" ? { activity: params.activity } : {}),
    ...(params.fulfillmentMode !== "all"
      ? { mode: params.fulfillmentMode }
      : {}),
    ...(params.page > 1 ? { page: String(params.page) } : {}),
    ...(params.limit !== 20 ? { limit: String(params.limit) } : {}),
  };
}
