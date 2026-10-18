import { httpClient } from "@/app/providers/http/http-client";
import { contactPointPayload } from "@/modules/contact-points";
import type { ContactPointArrays } from "@/modules/contact-points";
import type { CompanyDto, ContactDto, ContactPointsDto } from "./crm.dto";
import { mapCompany, mapContact, mapContactPoints } from "./crm.mapper";
import type {
  Company,
  CompanyInput,
  Contact,
  ContactInput,
  CrmContactPoints,
  CrmKind,
} from "../model/crm.types";

const root = (kind: CrmKind) => `/console/crm/${kind}`;
const item = (kind: CrmKind, id: string) => `${root(kind)}/${id}`;

export const crmContactsApi = {
  async list(signal?: AbortSignal): Promise<Contact[]> {
    const { data } = await httpClient.get<ContactDto[]>(root("contacts"), {
      signal,
    });
    return data.map(mapContact);
  },
  async get(id: string, signal?: AbortSignal): Promise<Contact> {
    const { data } = await httpClient.get<ContactDto>(item("contacts", id), {
      signal,
    });
    return mapContact(data);
  },
  async create(input: ContactInput): Promise<Contact> {
    const { data } = await httpClient.post<ContactDto>(root("contacts"), {
      first_name: input.firstName,
      last_name: input.lastName,
      middle_name: input.middleName,
    });
    return mapContact(data);
  },
  async update(id: string, input: ContactInput): Promise<Contact> {
    const { data } = await httpClient.put<ContactDto>(item("contacts", id), {
      first_name: input.firstName,
      last_name: input.lastName,
      middle_name: input.middleName,
    });
    return mapContact(data);
  },
  async delete(id: string): Promise<void> {
    await httpClient.delete(item("contacts", id));
  },
};

export const crmCompaniesApi = {
  async list(signal?: AbortSignal): Promise<Company[]> {
    const { data } = await httpClient.get<CompanyDto[]>(root("companies"), {
      signal,
    });
    return data.map(mapCompany);
  },
  async get(id: string, signal?: AbortSignal): Promise<Company> {
    const { data } = await httpClient.get<CompanyDto>(item("companies", id), {
      signal,
    });
    return mapCompany(data);
  },
  async create(input: CompanyInput): Promise<Company> {
    const { data } = await httpClient.post<CompanyDto>(root("companies"), {
      legal_name: input.legalName,
    });
    return mapCompany(data);
  },
  async update(id: string, input: CompanyInput): Promise<Company> {
    const { data } = await httpClient.put<CompanyDto>(item("companies", id), {
      legal_name: input.legalName,
    });
    return mapCompany(data);
  },
  async delete(id: string): Promise<void> {
    await httpClient.delete(item("companies", id));
  },
};

export const crmRelationsApi = {
  async companies(contactId: string, signal?: AbortSignal): Promise<Company[]> {
    const { data } = await httpClient.get<CompanyDto[]>(
      `${item("contacts", contactId)}/companies`,
      { signal },
    );
    return data.map(mapCompany);
  },
  async contacts(companyId: string, signal?: AbortSignal): Promise<Contact[]> {
    const { data } = await httpClient.get<ContactDto[]>(
      `${item("companies", companyId)}/contacts`,
      { signal },
    );
    return data.map(mapContact);
  },
  async link(kind: CrmKind, ownerId: string, relatedId: string): Promise<void> {
    const related = kind === "contacts" ? "companies" : "contacts";
    await httpClient.put(`${item(kind, ownerId)}/${related}/${relatedId}`);
  },
  async unlink(
    kind: CrmKind,
    ownerId: string,
    relatedId: string,
  ): Promise<void> {
    const related = kind === "contacts" ? "companies" : "contacts";
    await httpClient.delete(`${item(kind, ownerId)}/${related}/${relatedId}`);
  },
};

export const crmContactPointsApi = {
  async get(
    kind: CrmKind,
    id: string,
    signal?: AbortSignal,
  ): Promise<CrmContactPoints> {
    const { data } = await httpClient.get<ContactPointsDto>(
      `${item(kind, id)}/contact-points`,
      { signal },
    );
    return mapContactPoints(data);
  },
  async replace(
    kind: CrmKind,
    id: string,
    points: ContactPointArrays,
  ): Promise<CrmContactPoints> {
    const { data } = await httpClient.put<ContactPointsDto>(
      `${item(kind, id)}/contact-points`,
      {
        phones: contactPointPayload(points.phones, "phone"),
        emails: contactPointPayload(points.emails, "email"),
      },
    );
    return mapContactPoints(data);
  },
};
