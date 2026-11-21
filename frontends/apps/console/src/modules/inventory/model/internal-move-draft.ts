import type {
  InternalMoveDraftValues,
  InternalMoveDraftLine,
  InternalMoveErrors,
} from "./internal-move.types.ts";
export function emptyInternalMoveDraft(): InternalMoveDraftValues {
  return {
    warehouseId: "",
    warehouseName: "",
    ownerId: "",
    ownerName: "",
    lines: [],
  };
}
export function newInternalMoveLine(key: string): InternalMoveDraftLine {
  return {
    key,
    inventoryItemId: "",
    sku: "",
    baseUom: "",
    quantity: "1",
    uom: "",
  };
}
export function copyInternalMoveDraft(
  v: InternalMoveDraftValues,
): InternalMoveDraftValues {
  return { ...v, lines: v.lines.map((l) => ({ ...l })) };
}
export function normalizeInternalMoveQuantity(value: string): string {
  return value.trim().replace(",", ".");
}
export function internalMovePayloadSignature(
  v: InternalMoveDraftValues,
): string {
  return JSON.stringify({
    warehouseId: v.warehouseId,
    ownerId: v.ownerId,
    lines: v.lines.map((l) => ({
      inventoryItemId: l.inventoryItemId,
      quantity: normalizeInternalMoveQuantity(l.quantity),
      uom: l.uom,
    })),
  });
}
export function validateInternalMoveDraft(
  v: InternalMoveDraftValues,
): InternalMoveErrors {
  const e: InternalMoveErrors = { lineFields: {} };
  if (!v.warehouseId) e.warehouseId = "Выберите склад.";
  if (!v.ownerId) e.ownerId = "Выберите компанию-владельца.";
  if (v.lines.length > 100) e.lines = "В документе допустимо до 100 строк.";
  for (const l of v.lines) {
    const f: InternalMoveErrors["lineFields"][string] = {};
    if (!l.inventoryItemId) f.inventoryItemId = "Выберите SKU.";
    const q = normalizeInternalMoveQuantity(l.quantity);
    if (q.length > 128 || !/^\d+(?:\.\d+)?$/.test(q) || !/[1-9]/.test(q))
      f.quantity = "Укажите положительное десятичное количество.";
    if (!l.uom) f.uom = "Выберите единицу.";
    if (Object.keys(f).length) e.lineFields[l.key] = f;
  }
  return e;
}
export function hasInternalMoveErrors(e: InternalMoveErrors): boolean {
  return (
    !!e.warehouseId ||
    !!e.ownerId ||
    !!e.lines ||
    Object.keys(e.lineFields).length > 0
  );
}
export class InternalMoveCreationAttempt {
  private attempt: {
    key: string;
    signature: string;
    values: InternalMoveDraftValues;
  } | null = null;
  uncertain = false;
  begin(
    values: InternalMoveDraftValues,
    key: () => string,
  ): { key: string; values: InternalMoveDraftValues } {
    const signature = internalMovePayloadSignature(values);
    if (this.uncertain && this.attempt && this.attempt.signature !== signature)
      throw new Error("Сначала повторите исходный запрос с тем же ключом.");
    if (!this.attempt || this.attempt.signature !== signature)
      this.attempt = {
        key: key(),
        signature,
        values: copyInternalMoveDraft(values),
      };
    if (!this.uncertain) this.attempt.values = copyInternalMoveDraft(values);
    return {
      key: this.attempt.key,
      values: copyInternalMoveDraft(this.attempt.values),
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
