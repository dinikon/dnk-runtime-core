import type { ListParams } from "./crm.types";

export const contactKeys = {
  all: ["crm", "contacts"] as const,
  list: (params: ListParams) => [...contactKeys.all, "list", params] as const,
  detail: (id: string) => [...contactKeys.all, "detail", id] as const,
};

export const companyKeys = {
  all: ["crm", "companies"] as const,
  list: (params: ListParams) => [...companyKeys.all, "list", params] as const,
  detail: (id: string) => [...companyKeys.all, "detail", id] as const,
};
