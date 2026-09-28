import type { ContactDetailsDto, CompanyDetailsDto } from "./crm.dto";
import type { ContactDetails, CompanyDetails } from "../model/crm.types";
import { mapContactDetails, mapCompanyDetails } from "./crm.mapper";
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
    company_ids: input.companyIds,
    ...(input.expectedCompanyIds
      ? { expected_company_ids: input.expectedCompanyIds }
      : {}),
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
  async get(id: string, signal?: AbortSignal): Promise<ContactDetails> {
    const { data } = await httpClient.get<ContactDetailsDto>(
      `/console/crm/contacts/${id}`,
      { signal },
    );
    return mapContactDetails(data);
  },
  async create(input: ContactInput): Promise<ContactDetails> {
    const { data } = await httpClient.post<ContactDetailsDto>(
      "/console/crm/contacts",
      contactPayload(input),
    );
    return mapContactDetails(data);
  },
  async update(id: string, input: ContactInput): Promise<ContactDetails> {
    const { data } = await httpClient.put<ContactDetailsDto>(
      `/console/crm/contacts/${id}`,
      contactPayload(input),
    );
    return mapContactDetails(data);
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
  async get(id: string, signal?: AbortSignal): Promise<CompanyDetails> {
    const { data } = await httpClient.get<CompanyDetailsDto>(
      `/console/crm/companies/${id}`,
      { signal },
    );
    return mapCompanyDetails(data);
  },
  async create(input: CompanyInput): Promise<CompanyDetails> {
    const { data } = await httpClient.post<CompanyDetailsDto>(
      "/console/crm/companies",
      {
        contact_ids: input.contactIds,
        ...(input.expectedContactIds
          ? { expected_contact_ids: input.expectedContactIds }
          : {}),
        name: input.name,
        phones: contactPointPayload(input.phones, "phone"),
        emails: contactPointPayload(input.emails, "email"),
      },
    );
    return mapCompanyDetails(data);
  },
  async update(id: string, input: CompanyInput): Promise<CompanyDetails> {
    const { data } = await httpClient.put<CompanyDetailsDto>(
      `/console/crm/companies/${id}`,
      {
        contact_ids: input.contactIds,
        ...(input.expectedContactIds
          ? { expected_contact_ids: input.expectedContactIds }
          : {}),
        name: input.name,
        phones: contactPointPayload(input.phones, "phone"),
        emails: contactPointPayload(input.emails, "email"),
      },
    );
    return mapCompanyDetails(data);
  },
  async delete(id: string): Promise<void> {
    await httpClient.delete(`/console/crm/companies/${id}`);
  },
};

export const crmLinksApi = {
  async companies(
    contactId: string | undefined,
    params: ListParams,
    signal?: AbortSignal,
  ): Promise<Page<Company>> {
    if (!contactId) return crmCompaniesApi.list(params, signal);
    const { data } = await httpClient.get<PageDto<CompanyDto>>(
      `/console/crm/contacts/${contactId}/available-companies`,
      { params, signal },
    );
    return mapPage(data, mapCompany);
  },
  async contacts(
    companyId: string | undefined,
    params: ListParams,
    signal?: AbortSignal,
  ): Promise<Page<Contact>> {
    if (!companyId) return crmContactsApi.list(params, signal);
    const { data } = await httpClient.get<PageDto<ContactDto>>(
      `/console/crm/companies/${companyId}/available-contacts`,
      { params, signal },
    );
    return mapPage(data, mapContact);
  },
};
