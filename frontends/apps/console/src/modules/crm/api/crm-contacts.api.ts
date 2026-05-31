import { httpClient } from "@/app/providers/http";
import type {
  Contact,
  ContactFieldsResponse,
  CreateContactPayload,
  ListContactsResponse,
  UpdateContactPayload,
} from "@/modules/crm/api/types";

export const crmContactsApi = {
  describeFields: async () =>
    (await httpClient.post<ContactFieldsResponse>("/crm/contacts/fields")).data,
  list: async (params: { limit?: number; offset?: number } = {}) =>
    (await httpClient.get<ListContactsResponse>("/crm/contacts", { params }))
      .data,
  get: async (contactId: string) =>
    (await httpClient.get<Contact>(`/crm/contacts/${contactId}`)).data,
  create: async (payload: CreateContactPayload) =>
    (await httpClient.post<Contact>("/crm/contacts", payload)).data,
  update: async (contactId: string, payload: UpdateContactPayload) =>
    (await httpClient.put<Contact>(`/crm/contacts/${contactId}`, payload)).data,
  delete: async (contactId: string) => {
    await httpClient.delete(`/crm/contacts/${contactId}`);
  },
};
