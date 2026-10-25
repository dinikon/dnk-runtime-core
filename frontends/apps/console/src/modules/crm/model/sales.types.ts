import type { Contact } from "./crm.types";
import type { ContactPointArrays } from "@/modules/contact-points";
export type SalesKind = "leads" | "deals";
export type ConversionMode =
  | "contact"
  | "company"
  | "contact_company"
  | "contact_deal"
  | "company_deal"
  | "contact_company_deal"
  | "deal";
export interface SaleSummary {
  id: string;
  kind: SalesKind;
  title: string;
  funnelId: string;
  stageId: string;
  positionRevision: number;
  updatedAt: string;
  firstName?: string | null;
  lastName?: string | null;
  companyName?: string | null;
  contactIds: string[];
  companyIds: string[];
  conversionResult: ConversionResult | null;
  currency: string;
  total: string;
}
export interface BasketLine {
  id?: string;
  clientLineKey: string;
  name: string;
  kind: "product" | "service";
  quantity: string;
  unitPrice: string;
  lineTotal?: string;
  unit: string;
  catalogItemId: string | null;
  sku: string | null;
  customFields: Record<string, string>;
}
export interface SaleBasket {
  id: string;
  currency: string;
  revision: number;
  state: "editable" | "frozen";
  total: string;
  items: BasketLine[];
}
export interface SaleRecord extends SaleSummary {
  createdAt: string;
  firstName: string | null;
  lastName: string | null;
  middleName: string | null;
  companyName: string | null;
  contactId: string | null;
  companyId: string | null;
  sourceLeadId: string | null;
  sourceLeadSnapshot: Record<string, string | null> | null;
  lifecycleState: string;
  basket: SaleBasket;
  points: ContactPointArrays;
}
export interface SaleDraft {
  title: string;
  currency: string;
  funnelId: string;
  firstName: string;
  lastName: string;
  middleName: string;
  companyName: string;
  contactId: string | null;
  companyId: string | null;
  contactIds: string[];
  companyIds: string[];
  points: ContactPointArrays;
  items: BasketLine[];
  basketRevision?: number;
}
export interface SalesPage {
  items: SaleSummary[];
  total: number;
  offset: number;
  limit: number;
}
export interface ConversionResult {
  conversionId: string;
  mode: ConversionMode;
  contactId: string | null;
  companyId: string | null;
  dealId: string | null;
  basketId: string | null;
  convertedAt: string;
  convertedBy: string;
  replay: boolean;
}
export interface ConversionContext {
  sourceToken: string;
  source: SaleRecord;
  availableCompanies: { id: string; legalName: string }[];
  modes: ConversionMode[];
}
export interface ConversionDraft {
  mode: ConversionMode | "";
  firstName: string;
  lastName: string;
  middleName: string;
  legalName: string;
  title: string;
  funnelId: string;
  additionalCompanyIds: string[];
  contactPoints: string[];
  companyPoints: string[];
  dealPoints: string[];
  links: { contactId: string | null; companyId: string | null }[];
}
export interface ConversionSubmission {
  mode: ConversionMode;
  expectedSourceToken: string;
  expectedBasketRevision: number;
  contactPoints?: string[];
  companyPoints?: string[];
  dealPoints?: string[];
  contact?: {
    firstName: string;
    lastName: string | null;
    middleName: string | null;
  };
  company?: { legalName: string };
  deal?: {
    title: string;
    funnelId: string | null;
    additionalCompanyIds: string[];
  };
  links: { contactId: string | null; companyId: string | null }[];
}
export interface CatalogChoice {
  id: string;
  title: string;
  price: string | null;
  currency: string | null;
  kind: "product" | "service";
  sku: string | null;
}
export interface SalesFilters {
  funnelId: string;
  stageId: string;
  search: string;
  converted: boolean | undefined;
  offset: number;
  sort: string;
}

export interface SourceContactPreview {
  name: string;
  values: string[];
}
export interface ContactSeed {
  contact: Contact;
  points: ContactPointArrays;
}
export interface CreateSaleInput {
  kind: SalesKind;
  draft: SaleDraft;
}
export interface UpdateSaleInput {
  kind: SalesKind;
  id: string;
  draft: SaleDraft;
  previous: SaleDraft;
}
export interface MoveSaleInput {
  record: SaleSummary;
  stageId?: string;
  funnelId?: string;
}
export interface ConvertLeadInput {
  id: string;
  submission: ConversionSubmission;
  key: string;
}
export interface SaveSaleResult {
  lineIdMap: Record<string, string>;
}
