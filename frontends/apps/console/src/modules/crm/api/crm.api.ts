import { contactPointPayload } from "@/modules/contact-points";
import { httpClient } from "@/app/providers/http/http-client";
import type { CompanyDto, ContactDto, PageDto } from "./crm.dto";
import { mapCompany, mapContact, mapPage } from "./crm.mapper";
import type {
  Company,
  CompanyInput,
  Contact,
  ContactInput,
  ListParams,
  Page,
} from "../model/crm.types";

function contactPayload(input: ContactInput) {
  return {
    first_name: input.firstName,
    last_name: input.lastName,
    middle_name: input.middleName,
    phones: contactPointPayload(input.phones, "phone"),
    emails: contactPointPayload(input.emails, "email"),
  };
}

export const crmContactsApi = {
  async list(params: ListParams, signal?: AbortSignal): Promise<Page<Contact>> {
    const { data } = await httpClient.get<PageDto<ContactDto>>(
      "/console/crm/contacts",
      { params, signal },
    );
    return mapPage(data, mapContact);
  },
  async get(id: string, signal?: AbortSignal): Promise<Contact> {
    const { data } = await httpClient.get<ContactDto>(
      `/console/crm/contacts/${id}`,
      { signal },
    );
    return mapContact(data);
  },
  async create(input: ContactInput): Promise<Contact> {
    const { data } = await httpClient.post<ContactDto>(
      "/console/crm/contacts",
      contactPayload(input),
    );
    return mapContact(data);
  },
  async update(id: string, input: ContactInput): Promise<Contact> {
    const { data } = await httpClient.put<ContactDto>(
      `/console/crm/contacts/${id}`,
      contactPayload(input),
    );
    return mapContact(data);
  },
  async delete(id: string): Promise<void> {
    await httpClient.delete(`/console/crm/contacts/${id}`);
  },
};

export const crmCompaniesApi = {
  async list(params: ListParams, signal?: AbortSignal): Promise<Page<Company>> {
    const { data } = await httpClient.get<PageDto<CompanyDto>>(
      "/console/crm/companies",
      { params, signal },
    );
    return mapPage(data, mapCompany);
  },
  async get(id: string, signal?: AbortSignal): Promise<Company> {
    const { data } = await httpClient.get<CompanyDto>(
      `/console/crm/companies/${id}`,
      { signal },
    );
    return mapCompany(data);
  },
  async create(input: CompanyInput): Promise<Company> {
    const { data } = await httpClient.post<CompanyDto>(
      "/console/crm/companies",
      {
        name: input.name,
        phones: contactPointPayload(input.phones, "phone"),
        emails: contactPointPayload(input.emails, "email"),
      },
    );
    return mapCompany(data);
  },
  async update(id: string, input: CompanyInput): Promise<Company> {
    const { data } = await httpClient.put<CompanyDto>(
      `/console/crm/companies/${id}`,
      {
        name: input.name,
        phones: contactPointPayload(input.phones, "phone"),
        emails: contactPointPayload(input.emails, "email"),
      },
    );
    return mapCompany(data);
  },
  async delete(id: string): Promise<void> {
    await httpClient.delete(`/console/crm/companies/${id}`);
  },
};
