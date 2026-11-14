import type {
  FulfillmentMode,
  SupplierModelKey,
  SourceValues,
} from "./supplier-source.types";
export const fulfillmentLabels: Record<FulfillmentMode, string> = {
  DROPSHIP: "Дропшиппинг",
  PURCHASE_TO_WAREHOUSE: "Закупка на склад",
};
export function emptySource(): SourceValues {
  return {
    supplierModelKey: "crm.company",
    supplierId: "",
    name: "",
    externalWarehouseCode: "",
    fulfillmentModes: [],
    leadTimeSeconds: "",
    ttlSeconds: "",
    staleBehavior: "MARK_UNKNOWN",
    missingSkuBehavior: "MARK_UNKNOWN",
    isActive: true,
  };
}

export const supplierTypeLabels: Record<SupplierModelKey, string> = {
  "crm.company": "Компания",
  "crm.contact": "Контакт",
};
