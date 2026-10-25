import type {
  BasketInputDto,
  LeadDataInputDto,
  DealDataInputDto,
  ConvertLeadDto,
} from "./sales.dto";
import { mapContactPoint, contactPointPayload } from "@/modules/contact-points";
import type {
  LeadRowDto,
  DealRowDto,
  LeadDetailsDto,
  DealDetailsDto,
  ConversionResultDto,
  ConversionContextDto,
} from "./sales.dto";
import type {
  SaleSummary,
  SaleRecord,
  SaleDraft,
  ConversionResult,
  ConversionContext,
  ConversionSubmission,
} from "../model/sales.types";
export function mapConversion(v: ConversionResultDto): ConversionResult {
  return {
    conversionId: v.conversion_id,
    mode: v.mode,
    contactId: v.contact_id,
    companyId: v.company_id,
    dealId: v.deal_id,
    basketId: v.basket_id,
    convertedAt: v.converted_at,
    convertedBy: v.converted_by,
    replay: v.replay ?? false,
  };
}
export function mapLeadRow(v: LeadRowDto): SaleSummary {
  return {
    id: v.id,
    kind: "leads",
    title: v.title,
    funnelId: v.funnel_id,
    stageId: v.stage_id,
    positionRevision: v.position_revision,
    updatedAt: v.updated_at,
    firstName: v.first_name,
    lastName: v.last_name,
    companyName: v.company_name,
    contactIds: v.contact_id ? [v.contact_id] : [],
    companyIds: v.company_id ? [v.company_id] : [],
    conversionResult: v.conversion_result
      ? mapConversion(v.conversion_result)
      : null,
    currency: v.basket.currency,
    total: v.basket.total,
  };
}
export function mapDealRow(v: DealRowDto): SaleSummary {
  return {
    id: v.id,
    kind: "deals",
    title: v.title,
    funnelId: v.funnel_id,
    stageId: v.stage_id,
    positionRevision: v.position_revision,
    updatedAt: v.updated_at,
    firstName: v.source_lead_snapshot?.first_name,
    lastName: v.source_lead_snapshot?.last_name,
    companyName: v.source_lead_snapshot?.company_name,
    contactIds: v.contact_ids,
    companyIds: v.company_ids,
    conversionResult: null,
    currency: v.basket.currency,
    total: v.basket.total,
  };
}
function details(v: LeadDetailsDto | DealDetailsDto) {
  return {
    createdAt: v.created_at,
    basket: {
      id: v.basket.id,
      currency: v.basket.currency,
      revision: v.basket.revision,
      state: v.basket.state,
      total: v.basket.total,
      items: v.basket.items.map((i) => ({
        id: i.id,
        clientLineKey: i.id,
        name: i.name,
        kind: i.kind,
        quantity: i.quantity,
        unitPrice: i.unit_price,
        lineTotal: i.line_total,
        unit: i.unit,
        catalogItemId: i.catalog_item_id,
        sku: i.sku,
        customFields: { ...i.custom_fields },
      })),
    },
    points: {
      phones: v.points.phones.map(mapContactPoint),
      emails: v.points.emails.map(mapContactPoint),
    },
  };
}
export function mapLead(v: LeadDetailsDto): SaleRecord {
  return {
    ...mapLeadRow(v),
    ...details(v),
    firstName: v.first_name,
    lastName: v.last_name,
    middleName: v.middle_name,
    companyName: v.company_name,
    contactId: v.contact_id,
    companyId: v.company_id,
    sourceLeadId: null,
    sourceLeadSnapshot: null,
    lifecycleState: "draft",
  };
}
export function mapDeal(v: DealDetailsDto): SaleRecord {
  return {
    ...mapDealRow(v),
    ...details(v),
    firstName: null,
    lastName: null,
    middleName: null,
    companyName: null,
    contactId: null,
    companyId: null,
    sourceLeadId: v.source_lead_id,
    sourceLeadSnapshot: v.source_lead_snapshot,
    lifecycleState: v.lifecycle_state,
  };
}
export function mapContext(v: ConversionContextDto): ConversionContext {
  return {
    sourceToken: v.source_token,
    source: mapLead(v.source),
    availableCompanies: v.available_companies.map((c) => ({
      id: c.id,
      legalName: c.legal_name,
    })),
    modes: v.modes,
  };
}
export function basketPayload(v: SaleDraft): BasketInputDto {
  return {
    currency: v.currency,
    items: v.items.map((i) => ({
      ...(i.id ? { id: i.id } : { client_line_key: i.clientLineKey }),
      name: i.name,
      kind: i.kind,
      quantity: i.quantity.trim().replace(",", "."),
      unit_price: i.unitPrice.trim().replace(",", "."),
      unit: i.unit,
      catalog_item_id: i.catalogItemId,
      sku: i.sku,
      custom_fields: i.customFields,
    })),
    ...(v.basketRevision ? { expected_revision: v.basketRevision } : {}),
  };
}
export function leadPayload(v: SaleDraft): LeadDataInputDto {
  return {
    title: v.title,
    first_name: v.firstName || null,
    last_name: v.lastName || null,
    middle_name: v.middleName || null,
    company_name: v.companyName || null,
    contact_id: v.contactId,
    company_id: v.companyId,
    phones: contactPointPayload(v.points.phones, "phone"),
    emails: contactPointPayload(v.points.emails, "email"),
    basket: basketPayload(v),
  };
}
export function dealPayload(v: SaleDraft): DealDataInputDto {
  return {
    title: v.title,
    contact_ids: v.contactIds,
    company_ids: v.companyIds,
    basket: basketPayload(v),
  };
}
export function conversionPayload(v: ConversionSubmission): ConvertLeadDto {
  return {
    mode: v.mode,
    expected_source_token: v.expectedSourceToken,
    expected_basket_revision: v.expectedBasketRevision,
    ...(v.contactPoints ? { contact_points: v.contactPoints } : {}),
    ...(v.companyPoints ? { company_points: v.companyPoints } : {}),
    ...(v.dealPoints ? { deal_points: v.dealPoints } : {}),
    ...(v.contact
      ? {
          contact: {
            first_name: v.contact.firstName,
            last_name: v.contact.lastName,
            middle_name: v.contact.middleName,
          },
        }
      : {}),
    ...(v.company ? { company: { legal_name: v.company.legalName } } : {}),
    ...(v.deal
      ? {
          deal: {
            title: v.deal.title,
            funnel_id: v.deal.funnelId,
            additional_company_ids: v.deal.additionalCompanyIds,
          },
        }
      : {}),
    links: v.links.map((l) => ({
      contact_id: l.contactId,
      company_id: l.companyId,
    })),
  };
}
