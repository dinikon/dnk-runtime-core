import type { CrmKind } from "./crm.types";

export const CRM_QUERY_STALE_TIME = 30_000;

export const crmKeys = {
  all: ["crm"] as const,
  list: (kind: CrmKind) => ["crm", kind, "list"] as const,
  detail: (kind: CrmKind, id: string) => ["crm", kind, "detail", id] as const,
  relations: (kind: CrmKind, id: string) =>
    ["crm", kind, "relations", id] as const,
  points: (kind: CrmKind, id: string) =>
    ["crm", kind, "contact-points", id] as const,
};
