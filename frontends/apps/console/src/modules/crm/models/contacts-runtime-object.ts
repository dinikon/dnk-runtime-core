import { crmContactsApi } from "@/modules/crm/api";
import type { Contact } from "@/modules/crm/api/types";
import type { RuntimeObjectResource } from "@/shared/runtime-object";

export const contactsRuntimeObject: RuntimeObjectResource<Contact> = {
  key: "crm.contact",
  describeFields: crmContactsApi.describeFields,
  search: crmContactsApi.search,
  get: crmContactsApi.get,
  create: crmContactsApi.create,
  update: crmContactsApi.update,
  delete: crmContactsApi.delete,
};
