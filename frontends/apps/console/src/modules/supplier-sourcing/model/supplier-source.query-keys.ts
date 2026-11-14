import type { SupplierScope, SourcesParams } from "./supplier-source.types";
export const sourceKeys = {
  root: (scope: SupplierScope) =>
    ["supplier-sourcing", ...scope, "sources"] as const,
  lists: (scope: SupplierScope) => [...sourceKeys.root(scope), "list"] as const,
  list: (scope: SupplierScope, params: SourcesParams) =>
    [...sourceKeys.lists(scope), { ...params }] as const,
  detail: (scope: SupplierScope, id: string) =>
    [...sourceKeys.root(scope), "detail", id] as const,
  create: (scope: SupplierScope) =>
    [...sourceKeys.root(scope), "create"] as const,
  update: (scope: SupplierScope) =>
    [...sourceKeys.root(scope), "update"] as const,
};
