import type { SalesKind, SalesFilters } from "./sales.types";
type Scope = readonly (string | null)[];
export const salesKeys = {
  contactPreview: (scope: Scope, id: string | null) =>
    ["sales-contact-preview", ...scope, id] as const,
  people: (scope: Scope, type: "contacts" | "companies") =>
    ["sales-" + type, ...scope] as const,
  detail: (scope: Scope, kind: SalesKind, id: string) =>
    ["sales-detail", ...scope, kind, id] as const,
  list: (scope: Scope, kind: SalesKind, filters: SalesFilters) =>
    ["sales-list", ...scope, kind, filters] as const,
  column: (scope: Scope, kind: SalesKind, filters: SalesFilters) =>
    ["sales-column", ...scope, kind, filters] as const,
  conversion: (scope: Scope, id: string) =>
    ["sales-conversion", ...scope, id] as const,
  catalog: (scope: Scope, search: string) =>
    ["sales-catalog", ...scope, search] as const,
};
