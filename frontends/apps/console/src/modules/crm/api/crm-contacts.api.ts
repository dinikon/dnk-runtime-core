import { httpClient } from "@/app/providers/http";
import type {
  Contact,
  ContactFieldsResponse,
  CreateContactPayload,
  ListContactsResponse,
  UpdateContactPayload,
} from "@/modules/console/crm/api/types";
import type {
  RuntimeObjectMutationPayload,
  RuntimeObjectSearchRequest,
  RuntimeObjectSearchResponse,
} from "@/shared/runtime-object";

export const crmContactsApi = {
  describeFields: async () =>
    (
      await httpClient.get<ContactFieldsResponse>(
        "/console/crm/contacts/fields",
      )
    ).data,
  search: async (payload: RuntimeObjectSearchRequest) =>
    (
      await httpClient.post<RuntimeObjectSearchResponse<Contact>>(
        "/console/crm/contacts/search",
        payload,
      )
    ).data,
  list: async (params: { limit?: number; offset?: number } = {}) =>
    (
      await httpClient.get<ListContactsResponse>("/console/crm/contacts", {
        params,
      })
    ).data,
  get: async (contactId: string) =>
    (await httpClient.get<Contact>(`/console/crm/contacts/${contactId}`)).data,
  create: async (
    payload: CreateContactPayload | RuntimeObjectMutationPayload,
  ) => (await httpClient.post<Contact>("/console/crm/contacts", payload)).data,
  update: async (
    contactId: string,
    payload: UpdateContactPayload | RuntimeObjectMutationPayload,
  ) =>
    (
      await httpClient.put<Contact>(
        `/console/crm/contacts/${contactId}`,
        payload,
      )
    ).data,
  delete: async (contactId: string) => {
    await httpClient.delete(`/console/crm/contacts/${contactId}`);
  },
};
