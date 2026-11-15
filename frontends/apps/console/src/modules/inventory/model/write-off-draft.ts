import type {
  WriteOffDraftValues,
  WriteOffDraftLine,
  WriteOffErrors,
} from "./write-off.types.ts";
export function emptyWriteOffDraft(): WriteOffDraftValues {
  return {
    warehouseId: "",
    warehouseName: "",
    ownerId: "",
    ownerName: "",
    reason: "",
    lines: [],
  };
}
export function newWriteOffLine(key: string): WriteOffDraftLine {
  return {
    key,
    inventoryItemId: "",
    sku: "",
    baseUom: "",
    quantity: "1",
    uom: "",
  };
}
export function copyWriteOffDraft(v: WriteOffDraftValues): WriteOffDraftValues {
  return { ...v, lines: v.lines.map((l) => ({ ...l })) };
}
export function normalizeWriteOffQuantity(value: string): string {
  return value.trim().replace(",", ".");
}
export function writeOffPayloadSignature(v: WriteOffDraftValues): string {
  return JSON.stringify({
    warehouseId: v.warehouseId,
    ownerId: v.ownerId,
    reason: v.reason.trim(),
    lines: v.lines.map((l) => ({
      inventoryItemId: l.inventoryItemId,
      quantity: normalizeWriteOffQuantity(l.quantity),
      uom: l.uom,
    })),
  });
}
export function validateWriteOffDraft(v: WriteOffDraftValues): WriteOffErrors {
  const e: WriteOffErrors = { lineFields: {} };
  if (!v.reason.trim() || v.reason.trim().length > 1000)
    e.reason = "Укажите причину списания от 1 до 1000 символов.";
  if (!v.warehouseId) e.warehouseId = "Выберите склад.";
  if (!v.ownerId) e.ownerId = "Выберите компанию-владельца.";
  if (v.lines.length > 100) e.lines = "В документе допустимо до 100 строк.";
  for (const l of v.lines) {
    const f: WriteOffErrors["lineFields"][string] = {};
    if (!l.inventoryItemId) f.inventoryItemId = "Выберите SKU.";
    const q = normalizeWriteOffQuantity(l.quantity);
    if (q.length > 128 || !/^\d+(?:\.\d+)?$/.test(q) || !/[1-9]/.test(q))
      f.quantity = "Укажите положительное десятичное количество.";
    if (!l.uom) f.uom = "Выберите единицу.";
    if (Object.keys(f).length) e.lineFields[l.key] = f;
  }
  return e;
}
export function hasWriteOffErrors(e: WriteOffErrors): boolean {
  return (
    !!e.reason ||
    !!e.warehouseId ||
    !!e.ownerId ||
    !!e.lines ||
    Object.keys(e.lineFields).length > 0
  );
}
export class WriteOffCreationAttempt {
  private attempt: {
    key: string;
    signature: string;
    values: WriteOffDraftValues;
  } | null = null;
  uncertain = false;
  begin(
    values: WriteOffDraftValues,
    key: () => string,
  ): { key: string; values: WriteOffDraftValues } {
    const signature = writeOffPayloadSignature(values);
    if (this.uncertain && this.attempt && this.attempt.signature !== signature)
      throw new Error("Сначала повторите исходный запрос с тем же ключом.");
    if (!this.attempt || this.attempt.signature !== signature)
      this.attempt = {
        key: key(),
        signature,
        values: copyWriteOffDraft(values),
      };
    if (!this.uncertain) this.attempt.values = copyWriteOffDraft(values);
    return {
      key: this.attempt.key,
      values: copyWriteOffDraft(this.attempt.values),
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
