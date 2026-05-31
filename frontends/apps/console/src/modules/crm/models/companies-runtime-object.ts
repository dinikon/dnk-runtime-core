import { crmCompaniesApi } from "@/modules/crm/api";
import type { Company } from "@/modules/crm/api/types";
import type { RuntimeObjectResource } from "@/shared/runtime-object";

export const companiesRuntimeObject: RuntimeObjectResource<Company> = {
  key: "crm.company",
  describeFields: crmCompaniesApi.describeFields,
  search: crmCompaniesApi.search,
  get: crmCompaniesApi.get,
  create: crmCompaniesApi.create,
  update: crmCompaniesApi.update,
  delete: crmCompaniesApi.delete,
};
