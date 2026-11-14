import type {
  CreateSupplierSourceRequestDTO,
  PatchSupplierSourceRequestDTO,
  CreateSupplierSourceResponseDTO,
  ListSupplierSourcesResponseDTO,
  ListSupplierSourcesRequestDTO,
} from "./supplier-source.dto";
import type {
  SupplierSource,
  SourcesPage,
  SourceValues,
  SourceChanges,
  SourcesParams,
} from "../model/supplier-source.types";
export function sourceFromDto(
  dto: CreateSupplierSourceResponseDTO,
): SupplierSource {
  return {
    id: dto.id,
    supplierModelKey: dto.supplier_model_key,
    supplierId: dto.supplier_id,
    supplierName: dto.supplier_name,
    name: dto.name,
    externalWarehouseCode: dto.external_warehouse_code,
    fulfillmentModes: [...dto.fulfillment_modes],
    defaultLeadTimeSeconds: dto.default_lead_time_seconds,
    isActive: dto.is_active,
    stockUpdatePolicy: {
      ttlSeconds: dto.stock_update_policy.ttl_seconds,
      staleBehavior: dto.stock_update_policy.stale_behavior,
      missingSkuBehavior: dto.stock_update_policy.missing_sku_behavior,
    },
  };
}
export function sourceCreateToDto(
  value: SourceValues,
): CreateSupplierSourceRequestDTO {
  return {
    supplier_model_key: value.supplierModelKey,
    supplier_id: value.supplierId,
    name: value.name,
    external_warehouse_code: value.externalWarehouseCode.trim() || null,
    fulfillment_modes: [...value.fulfillmentModes],
    default_lead_time_seconds: Number(value.leadTimeSeconds),
    stock_update_policy: {
      ttl_seconds: Number(value.ttlSeconds),
      stale_behavior: value.staleBehavior,
      missing_sku_behavior: value.missingSkuBehavior,
    },
  };
}
export function sourcePatchToDto(
  value: SourceChanges,
): PatchSupplierSourceRequestDTO {
  const dto: PatchSupplierSourceRequestDTO = {};
  if (value.name !== undefined) dto.name = value.name;
  if (value.externalWarehouseCode !== undefined)
    dto.external_warehouse_code = value.externalWarehouseCode;
  if (value.fulfillmentModes !== undefined)
    dto.fulfillment_modes = [...value.fulfillmentModes];
  if (value.defaultLeadTimeSeconds !== undefined)
    dto.default_lead_time_seconds = value.defaultLeadTimeSeconds;
  if (value.isActive !== undefined) dto.is_active = value.isActive;
  if (value.stockUpdatePolicy !== undefined)
    dto.stock_update_policy = {
      ttl_seconds: value.stockUpdatePolicy.ttlSeconds,
      stale_behavior: value.stockUpdatePolicy.staleBehavior,
      missing_sku_behavior: value.stockUpdatePolicy.missingSkuBehavior,
    };
  return dto;
}
export function sourcesPageFromDto(
  dto: ListSupplierSourcesResponseDTO,
): SourcesPage {
  return { ...dto, items: dto.items.map(sourceFromDto) };
}
export function sourcesParamsToDto(
  value: SourcesParams,
): ListSupplierSourcesRequestDTO {
  return {
    offset: (value.page - 1) * value.limit,
    limit: value.limit,
    search: value.search || undefined,
    supplier_model_key: value.supplierModelKey || undefined,
    supplier_id: value.supplierId || undefined,
    is_active:
      value.activity === "all" ? undefined : value.activity === "active",
    fulfillment_mode:
      value.fulfillmentMode === "all" ? undefined : value.fulfillmentMode,
  };
}
