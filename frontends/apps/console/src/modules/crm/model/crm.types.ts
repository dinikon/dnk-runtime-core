export interface CrmLink {
  id: string;
  name: string;
}

import type { ContactPointArrays } from "@/modules/contact-points";
export interface AuditFields {
  id: string;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  updatedBy: string;
}

export interface Contact extends AuditFields, ContactPointArrays {
  firstName: string;
  lastName: string | null;
  middleName: string | null;
  displayName: string;
}

export interface Company extends AuditFields, ContactPointArrays {
  name: string;
}

export interface ContactDetails extends Contact {
  companies: CrmLink[];
}
export interface CompanyDetails extends Company {
  contacts: CrmLink[];
}

export interface ContactInput extends ContactPointArrays {
  companyIds: string[];
  expectedCompanyIds?: string[];
  firstName: string;
  lastName: string | null;
  middleName: string | null;
}

export interface CompanyInput extends ContactPointArrays {
  contactIds: string[];
  expectedContactIds?: string[];
  name: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ListParams {
  q: string;
  limit: number;
  offset: number;
}
