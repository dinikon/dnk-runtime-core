import { httpClient } from "@/app/providers/http";
import type {
  Contact,
  ContactFieldsResponse,
  CreateContactPayload,
  ListContactsResponse,
  UpdateContactPayload,
} from "@/modules/crm/api/types";
import type {
  RuntimeObjectMutationPayload,
  RuntimeObjectSearchRequest,
  RuntimeObjectSearchResponse,
} from "@/shared/runtime-object";

export const crmContactsApi = {
  describeFields: async () =>
    (await httpClient.get<ContactFieldsResponse>("/crm/contacts/fields")).data,
  search: async (payload: RuntimeObjectSearchRequest) =>
    (
      await httpClient.post<RuntimeObjectSearchResponse<Contact>>(
        "/crm/contacts/search",
        payload,
      )
    ).data,
  list: async (params: { limit?: number; offset?: number } = {}) =>
    (await httpClient.get<ListContactsResponse>("/crm/contacts", { params }))
      .data,
  get: async (contactId: string) =>
    (await httpClient.get<Contact>(`/crm/contacts/${contactId}`)).data,
  create: async (
    payload: CreateContactPayload | RuntimeObjectMutationPayload,
  ) => (await httpClient.post<Contact>("/crm/contacts", payload)).data,
  update: async (
    contactId: string,
    payload: UpdateContactPayload | RuntimeObjectMutationPayload,
  ) =>
    (await httpClient.put<Contact>(`/crm/contacts/${contactId}`, payload)).data,
  delete: async (contactId: string) => {
    await httpClient.delete(`/crm/contacts/${contactId}`);
  },
};
