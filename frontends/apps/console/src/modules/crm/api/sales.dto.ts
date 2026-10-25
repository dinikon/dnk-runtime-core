import type { ContactPointDto } from "@/modules/contact-points";
export interface ConversionResultDto {
  conversion_id: string;
  mode:
    | "contact"
    | "company"
    | "contact_company"
    | "contact_deal"
    | "company_deal"
    | "contact_company_deal"
    | "deal";
  contact_id: string | null;
  company_id: string | null;
  deal_id: string | null;
  basket_id: string | null;
  converted_at: string;
  converted_by: string;
  replay?: boolean;
}
export interface BasketItemDto {
  id: string;
  name: string;
  kind: "product" | "service";
  quantity: string;
  unit_price: string;
  line_total: string;
  unit: string;
  catalog_item_id: string | null;
  sku: string | null;
  custom_fields: Record<string, string>;
}
export interface BasketDto {
  id: string;
  currency: string;
  revision: number;
  state: "editable" | "frozen";
  total: string;
  items: BasketItemDto[];
}
interface SaleRowDto {
  id: string;
  title: string;
  funnel_id: string;
  stage_id: string;
  position_revision: number;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
  basket: { currency: string; total: string; revision: number };
}
export interface LeadRowDto extends SaleRowDto {
  first_name: string | null;
  last_name: string | null;
  middle_name: string | null;
  company_name: string | null;
  contact_id: string | null;
  company_id: string | null;
  conversion_result: ConversionResultDto | null;
}
export interface DealRowDto extends SaleRowDto {
  contact_ids: string[];
  company_ids: string[];
  source_lead_id: string | null;
  source_lead_snapshot: Record<string, string | null> | null;
  lifecycle_state: string;
}
export interface LeadDetailsDto extends LeadRowDto {
  basket: BasketDto;
  points: { phones: ContactPointDto[]; emails: ContactPointDto[] };
}
export interface DealDetailsDto extends DealRowDto {
  basket: BasketDto;
  points: { phones: ContactPointDto[]; emails: ContactPointDto[] };
}
export interface LeadPageDto {
  items: LeadRowDto[];
  total: number;
  offset: number;
  limit: number;
}
export interface DealPageDto {
  items: DealRowDto[];
  total: number;
  offset: number;
  limit: number;
}
export interface ConversionContextDto {
  source_token: string;
  source: LeadDetailsDto;
  available_companies: { id: string; legal_name: string }[];
  modes: ConversionResultDto["mode"][];
}
export interface SaleMutationDto {
  id: string;
  funnel_id: string;
  stage_id: string;
  position_revision: number;
  line_id_map: Record<string, string>;
}

export interface PointInputDto {
  value: string;
  binding_id: string | null;
  label_id: string | null;
  country_code?: string;
}
export interface BasketInputDto {
  currency: string;
  expected_revision?: number;
  items: {
    id?: string;
    client_line_key?: string;
    name: string;
    kind: "product" | "service";
    quantity: string;
    unit_price: string;
    unit: string;
    catalog_item_id: string | null;
    sku: string | null;
    custom_fields: Record<string, string>;
  }[];
}
export interface LeadDataInputDto {
  title: string;
  first_name: string | null;
  last_name: string | null;
  middle_name: string | null;
  company_name: string | null;
  contact_id: string | null;
  company_id: string | null;
  phones: PointInputDto[];
  emails: PointInputDto[];
  basket: BasketInputDto;
}
export interface DealDataInputDto {
  title: string;
  contact_ids: string[];
  company_ids: string[];
  basket: BasketInputDto;
}
export interface CreateLeadDto extends LeadDataInputDto {
  funnel_id: string | null;
}
export interface CreateDealDto extends DealDataInputDto {
  funnel_id: string | null;
}
export type PatchLeadDto = Partial<LeadDataInputDto>;
export type PatchDealDto = Partial<DealDataInputDto>;
export interface ConvertLeadDto {
  mode: ConversionResultDto["mode"];
  expected_source_token: string;
  expected_basket_revision: number;
  contact_points?: string[];
  company_points?: string[];
  deal_points?: string[];
  contact?: {
    first_name: string;
    last_name: string | null;
    middle_name: string | null;
  };
  company?: { legal_name: string };
  deal?: {
    title: string;
    funnel_id: string | null;
    additional_company_ids: string[];
  };
  links: { contact_id: string | null; company_id: string | null }[];
}
