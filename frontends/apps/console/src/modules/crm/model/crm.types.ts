import type { ContactPointArrays } from "@/modules/contact-points";

export type CrmKind = "contacts" | "companies";

export interface AuditFields {
  id: string;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  updatedBy: string;
}

export interface Contact extends AuditFields {
  firstName: string;
  lastName: string | null;
  middleName: string | null;
  displayName: string;
}

export interface Company extends AuditFields {
  legalName: string;
}

export type CrmRecord = Contact | Company;
export type CrmContactPoints = ContactPointArrays;

export interface ContactInput {
  firstName: string;
  lastName: string | null;
  middleName: string | null;
}

export interface CompanyInput {
  legalName: string;
}
