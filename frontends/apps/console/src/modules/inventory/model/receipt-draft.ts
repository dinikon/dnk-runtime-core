import type {
  ReceiptDraftValues,
  ReceiptDraftLine,
  ReceiptErrors,
} from "./receipt.types.ts";
export function emptyReceiptDraft(): ReceiptDraftValues {
  return {
    warehouseId: "",
    warehouseName: "",
    ownerId: "",
    ownerName: "",
    lines: [],
  };
}
export function newReceiptLine(key: string): ReceiptDraftLine {
  return {
    key,
    inventoryItemId: "",
    sku: "",
    baseUom: "",
    quantity: "1",
    uom: "",
  };
}
export function copyReceiptDraft(v: ReceiptDraftValues): ReceiptDraftValues {
  return { ...v, lines: v.lines.map((l) => ({ ...l })) };
}
export function normalizeReceiptQuantity(value: string): string {
  return value.trim().replace(",", ".");
}
export function receiptPayloadSignature(v: ReceiptDraftValues): string {
  return JSON.stringify({
    warehouseId: v.warehouseId,
    ownerId: v.ownerId,
    lines: v.lines.map((l) => ({
      inventoryItemId: l.inventoryItemId,
      quantity: normalizeReceiptQuantity(l.quantity),
      uom: l.uom,
    })),
  });
}
export function validateReceiptDraft(v: ReceiptDraftValues): ReceiptErrors {
  const e: ReceiptErrors = { lineFields: {} };
  if (!v.warehouseId) e.warehouseId = "Выберите склад.";
  if (!v.ownerId) e.ownerId = "Выберите компанию-владельца.";
  if (v.lines.length > 100) e.lines = "В документе допустимо до 100 строк.";
  for (const l of v.lines) {
    const f: ReceiptErrors["lineFields"][string] = {};
    if (!l.inventoryItemId) f.inventoryItemId = "Выберите SKU.";
    const q = normalizeReceiptQuantity(l.quantity);
    if (q.length > 128 || !/^\d+(?:\.\d+)?$/.test(q) || !/[1-9]/.test(q))
      f.quantity = "Укажите положительное десятичное количество.";
    if (!l.uom) f.uom = "Выберите единицу.";
    if (Object.keys(f).length) e.lineFields[l.key] = f;
  }
  return e;
}
export function hasReceiptErrors(e: ReceiptErrors): boolean {
  return (
    !!e.warehouseId ||
    !!e.ownerId ||
    !!e.lines ||
    Object.keys(e.lineFields).length > 0
  );
}
export class ReceiptCreationAttempt {
  private attempt: {
    key: string;
    signature: string;
    values: ReceiptDraftValues;
  } | null = null;
  uncertain = false;
  begin(
    values: ReceiptDraftValues,
    key: () => string,
  ): { key: string; values: ReceiptDraftValues } {
    const signature = receiptPayloadSignature(values);
    if (this.uncertain && this.attempt && this.attempt.signature !== signature)
      throw new Error("Сначала повторите исходный запрос с тем же ключом.");
    if (!this.attempt || this.attempt.signature !== signature)
      this.attempt = {
        key: key(),
        signature,
        values: copyReceiptDraft(values),
      };
    if (!this.uncertain) this.attempt.values = copyReceiptDraft(values);
    return {
      key: this.attempt.key,
      values: copyReceiptDraft(this.attempt.values),
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
