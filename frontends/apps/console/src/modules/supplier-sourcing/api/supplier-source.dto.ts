import type {
  SupplierModelKey,
  FulfillmentMode,
  StaleBehavior,
  MissingSkuBehavior,
} from "../model/supplier-source.types";
export interface StockUpdatePolicyDTO {
  ttl_seconds: number;
  stale_behavior: StaleBehavior;
  missing_sku_behavior: MissingSkuBehavior;
}
export interface CreateSupplierSourceRequestDTO {
  supplier_model_key: SupplierModelKey;
  supplier_id: string;
  name: string;
  external_warehouse_code: string | null;
  fulfillment_modes: FulfillmentMode[];
  default_lead_time_seconds: number;
  stock_update_policy: StockUpdatePolicyDTO;
}
export interface PatchSupplierSourceRequestDTO {
  name?: string;
  external_warehouse_code?: string | null;
  fulfillment_modes?: FulfillmentMode[];
  default_lead_time_seconds?: number;
  stock_update_policy?: StockUpdatePolicyDTO;
  is_active?: boolean;
}
export interface CreateSupplierSourceResponseDTO {
  id: string;
  supplier_model_key: SupplierModelKey;
  supplier_id: string;
  supplier_name: string | null;
  name: string;
  external_warehouse_code: string | null;
  fulfillment_modes: FulfillmentMode[];
  default_lead_time_seconds: number;
  is_active: boolean;
  stock_update_policy: StockUpdatePolicyDTO;
}
export interface GetSupplierSourceResponseDTO {
  id: string;
  supplier_model_key: SupplierModelKey;
  supplier_id: string;
  supplier_name: string | null;
  name: string;
  external_warehouse_code: string | null;
  fulfillment_modes: FulfillmentMode[];
  default_lead_time_seconds: number;
  is_active: boolean;
  stock_update_policy: StockUpdatePolicyDTO;
}
export interface PatchSupplierSourceResponseDTO {
  id: string;
  supplier_model_key: SupplierModelKey;
  supplier_id: string;
  supplier_name: string | null;
  name: string;
  external_warehouse_code: string | null;
  fulfillment_modes: FulfillmentMode[];
  default_lead_time_seconds: number;
  is_active: boolean;
  stock_update_policy: StockUpdatePolicyDTO;
}
export interface ListSupplierSourceItemDTO {
  id: string;
  supplier_model_key: SupplierModelKey;
  supplier_id: string;
  supplier_name: string | null;
  name: string;
  external_warehouse_code: string | null;
  fulfillment_modes: FulfillmentMode[];
  default_lead_time_seconds: number;
  is_active: boolean;
  stock_update_policy: StockUpdatePolicyDTO;
}
export interface ListSupplierSourcesResponseDTO {
  items: ListSupplierSourceItemDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface ListSupplierSourcesRequestDTO {
  search?: string;
  supplier_model_key?: SupplierModelKey;
  supplier_id?: string;
  is_active?: boolean;
  fulfillment_mode?: FulfillmentMode;
  offset: number;
  limit: number;
}
