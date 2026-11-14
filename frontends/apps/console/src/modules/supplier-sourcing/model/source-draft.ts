import type {
  SupplierSource,
  SourceValues,
  SourceChanges,
  SourceFieldErrors,
} from "./supplier-source.types.ts";
export function sourceValues(source: SupplierSource): SourceValues {
  return {
    supplierModelKey: source.supplierModelKey,
    supplierId: source.supplierId,
    name: source.name,
    externalWarehouseCode: source.externalWarehouseCode ?? "",
    fulfillmentModes: [...source.fulfillmentModes],
    leadTimeSeconds: String(source.defaultLeadTimeSeconds),
    ttlSeconds: String(source.stockUpdatePolicy.ttlSeconds),
    staleBehavior: source.stockUpdatePolicy.staleBehavior,
    missingSkuBehavior: source.stockUpdatePolicy.missingSkuBehavior,
    isActive: source.isActive,
  };
}
export function snapshot(value: SourceValues): SourceValues {
  return { ...value, fulfillmentModes: [...value.fulfillmentModes] };
}
function sameModes(a: SourceValues, b: SourceValues): boolean {
  return (
    [...a.fulfillmentModes].sort().join() ===
    [...b.fulfillmentModes].sort().join()
  );
}
export function sourceChanges(
  value: SourceValues,
  baseline: SourceValues,
): SourceChanges {
  const result: SourceChanges = {};
  if (value.name !== baseline.name) result.name = value.name;
  if (value.externalWarehouseCode !== baseline.externalWarehouseCode)
    result.externalWarehouseCode = value.externalWarehouseCode.trim() || null;
  if (!sameModes(value, baseline))
    result.fulfillmentModes = [...value.fulfillmentModes];
  if (value.leadTimeSeconds !== baseline.leadTimeSeconds)
    result.defaultLeadTimeSeconds = Number(value.leadTimeSeconds);
  if (value.isActive !== baseline.isActive) result.isActive = value.isActive;
  if (
    value.ttlSeconds !== baseline.ttlSeconds ||
    value.staleBehavior !== baseline.staleBehavior ||
    value.missingSkuBehavior !== baseline.missingSkuBehavior
  )
    result.stockUpdatePolicy = {
      ttlSeconds: Number(value.ttlSeconds),
      staleBehavior: value.staleBehavior,
      missingSkuBehavior: value.missingSkuBehavior,
    };
  return result;
}
export function validateSource(value: SourceValues): SourceFieldErrors {
  const errors: SourceFieldErrors = {};
  if (!value.supplierId) errors.supplierId = "Выберите контрагента поставщика.";
  if (!value.name.trim() || /[\p{Cc}\p{Cf}]/u.test(value.name.trim()))
    errors.name = "Укажите название без управляющих символов.";
  if (/[\p{Cc}\p{Cf}]/u.test(value.externalWarehouseCode.trim()))
    errors.externalWarehouseCode = "Уберите управляющие символы.";
  if (!value.fulfillmentModes.length)
    errors.fulfillmentModes = "Выберите хотя бы один режим.";
  for (const key of ["ttlSeconds", "leadTimeSeconds"] as const) {
    const n = Number(value[key]);
    if (
      !/^\d+$/.test(value[key]) ||
      !Number.isSafeInteger(n) ||
      n > 86399999999999 ||
      n < (key === "ttlSeconds" ? 1 : 0)
    )
      errors[key] =
        key === "ttlSeconds"
          ? "TTL должен быть положительным целым числом секунд."
          : "Укажите неотрицательное целое число секунд.";
  }
  return errors;
}
export class SourceDraft {
  values: SourceValues | null = null;
  private baseline: SourceValues | null = null;
  get changes(): SourceChanges {
    return this.values && this.baseline
      ? sourceChanges(this.values, this.baseline)
      : {};
  }
  get dirty(): boolean {
    return Object.keys(this.changes).length > 0;
  }
  reset(value: SourceValues): void {
    this.values = snapshot(value);
    this.baseline = snapshot(value);
  }
  receive(value: SourceValues): void {
    if (!this.dirty) this.reset(value);
  }
  change(value: SourceValues): void {
    this.values = snapshot(value);
  }
  clear(): void {
    this.values = null;
    this.baseline = null;
  }
  acknowledge(sent: SourceValues, result: SourceValues): void {
    if (!this.values) return;
    const current = this.values;
    this.values = {
      supplierModelKey: result.supplierModelKey,
      supplierId: result.supplierId,
      name: current.name === sent.name ? result.name : current.name,
      externalWarehouseCode:
        current.externalWarehouseCode === sent.externalWarehouseCode
          ? result.externalWarehouseCode
          : current.externalWarehouseCode,
      fulfillmentModes: sameModes(current, sent)
        ? [...result.fulfillmentModes]
        : [...current.fulfillmentModes],
      leadTimeSeconds:
        current.leadTimeSeconds === sent.leadTimeSeconds
          ? result.leadTimeSeconds
          : current.leadTimeSeconds,
      ttlSeconds:
        current.ttlSeconds === sent.ttlSeconds
          ? result.ttlSeconds
          : current.ttlSeconds,
      staleBehavior:
        current.staleBehavior === sent.staleBehavior
          ? result.staleBehavior
          : current.staleBehavior,
      missingSkuBehavior:
        current.missingSkuBehavior === sent.missingSkuBehavior
          ? result.missingSkuBehavior
          : current.missingSkuBehavior,
      isActive:
        current.isActive === sent.isActive ? result.isActive : current.isActive,
    };
    this.baseline = snapshot(result);
  }
}
