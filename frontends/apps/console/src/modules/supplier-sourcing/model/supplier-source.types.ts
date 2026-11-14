export type SupplierModelKey = "crm.company" | "crm.contact";
export type FulfillmentMode = "DROPSHIP" | "PURCHASE_TO_WAREHOUSE";
export type StaleBehavior = "MARK_UNKNOWN" | "BLOCK_AUTOMATIC_SALE";
export type MissingSkuBehavior = "KEEP_LAST" | "MARK_UNKNOWN";
export interface StockUpdatePolicy {
  ttlSeconds: number;
  staleBehavior: StaleBehavior;
  missingSkuBehavior: MissingSkuBehavior;
}
export interface SupplierSource {
  id: string;
  supplierModelKey: SupplierModelKey;
  supplierId: string;
  supplierName: string | null;
  name: string;
  externalWarehouseCode: string | null;
  fulfillmentModes: FulfillmentMode[];
  defaultLeadTimeSeconds: number;
  isActive: boolean;
  stockUpdatePolicy: StockUpdatePolicy;
}
export interface SourcesPage {
  items: SupplierSource[];
  total: number;
  offset: number;
  limit: number;
}
export interface SourcesParams {
  search: string;
  supplierModelKey: SupplierModelKey | "";
  supplierId: string;
  activity: "all" | "active" | "inactive";
  fulfillmentMode: FulfillmentMode | "all";
  page: number;
  limit: number;
}
export interface SourceValues {
  supplierModelKey: SupplierModelKey;
  supplierId: string;
  name: string;
  externalWarehouseCode: string;
  fulfillmentModes: FulfillmentMode[];
  leadTimeSeconds: string;
  ttlSeconds: string;
  staleBehavior: StaleBehavior;
  missingSkuBehavior: MissingSkuBehavior;
  isActive: boolean;
}
export interface SourceChanges {
  name?: string;
  externalWarehouseCode?: string | null;
  fulfillmentModes?: FulfillmentMode[];
  defaultLeadTimeSeconds?: number;
  isActive?: boolean;
  stockUpdatePolicy?: StockUpdatePolicy;
}
export type SourceFieldErrors = Partial<Record<keyof SourceValues, string>>;
export type SupplierScope = readonly [string | null, string | null, string];
