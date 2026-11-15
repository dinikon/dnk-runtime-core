import type {
  StatusChangeDraftValues,
  StatusChangeDraftLine,
  StatusChangeErrors,
} from "./status-change.types.ts";
export function emptyStatusChangeDraft(): StatusChangeDraftValues {
  return {
    warehouseId: "",
    warehouseName: "",
    ownerId: "",
    ownerName: "",
    reason: "",
    targetStatus: "",
    lines: [],
  };
}
export function newStatusChangeLine(key: string): StatusChangeDraftLine {
  return {
    key,
    inventoryItemId: "",
    sku: "",
    baseUom: "",
    quantity: "1",
    uom: "",
  };
}
export function copyStatusChangeDraft(
  v: StatusChangeDraftValues,
): StatusChangeDraftValues {
  return { ...v, lines: v.lines.map((l) => ({ ...l })) };
}
export function normalizeStatusChangeQuantity(value: string): string {
  return value.trim().replace(",", ".");
}
export function statusChangePayloadSignature(
  v: StatusChangeDraftValues,
): string {
  return JSON.stringify({
    warehouseId: v.warehouseId,
    ownerId: v.ownerId,
    reason: v.reason.trim(),
    targetStatus: v.targetStatus,
    lines: v.lines.map((l) => ({
      inventoryItemId: l.inventoryItemId,
      quantity: normalizeStatusChangeQuantity(l.quantity),
      uom: l.uom,
    })),
  });
}
export function validateStatusChangeDraft(
  v: StatusChangeDraftValues,
): StatusChangeErrors {
  const e: StatusChangeErrors = { lineFields: {} };
  if (
    !["SELLABLE", "QUARANTINE", "DAMAGED", "BLOCKED"].includes(v.targetStatus)
  )
    e.targetStatus = "Выберите новое состояние.";
  if (!v.reason.trim() || v.reason.trim().length > 1000)
    e.reason = "Укажите причину изменения состояния от 1 до 1000 символов.";
  if (!v.warehouseId) e.warehouseId = "Выберите склад.";
  if (!v.ownerId) e.ownerId = "Выберите компанию-владельца.";
  if (v.lines.length > 100) e.lines = "В документе допустимо до 100 строк.";
  for (const l of v.lines) {
    const f: StatusChangeErrors["lineFields"][string] = {};
    if (!l.inventoryItemId) f.inventoryItemId = "Выберите SKU.";
    const q = normalizeStatusChangeQuantity(l.quantity);
    if (q.length > 128 || !/^\d+(?:\.\d+)?$/.test(q) || !/[1-9]/.test(q))
      f.quantity = "Укажите положительное десятичное количество.";
    if (!l.uom) f.uom = "Выберите единицу.";
    if (Object.keys(f).length) e.lineFields[l.key] = f;
  }
  return e;
}
export function hasStatusChangeErrors(e: StatusChangeErrors): boolean {
  return (
    !!e.reason ||
    !!e.targetStatus ||
    !!e.warehouseId ||
    !!e.ownerId ||
    !!e.lines ||
    Object.keys(e.lineFields).length > 0
  );
}
export class StatusChangeCreationAttempt {
  private attempt: {
    key: string;
    signature: string;
    values: StatusChangeDraftValues;
  } | null = null;
  uncertain = false;
  begin(
    values: StatusChangeDraftValues,
    key: () => string,
  ): { key: string; values: StatusChangeDraftValues } {
    const signature = statusChangePayloadSignature(values);
    if (this.uncertain && this.attempt && this.attempt.signature !== signature)
      throw new Error("Сначала повторите исходный запрос с тем же ключом.");
    if (!this.attempt || this.attempt.signature !== signature)
      this.attempt = {
        key: key(),
        signature,
        values: copyStatusChangeDraft(values),
      };
    if (!this.uncertain) this.attempt.values = copyStatusChangeDraft(values);
    return {
      key: this.attempt.key,
      values: copyStatusChangeDraft(this.attempt.values),
    };
  }
  fail(uncertain: boolean): void {
    this.uncertain = uncertain;
  }
  clear(): void {
    this.attempt = null;
    this.uncertain = false;
  }
}
