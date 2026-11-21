import type {
  IssueDraftValues,
  IssueDraftLine,
  IssueErrors,
} from "./issue.types.ts";
export function emptyIssueDraft(): IssueDraftValues {
  return {
    warehouseId: "",
    warehouseName: "",
    ownerId: "",
    ownerName: "",
    lines: [],
  };
}
export function newIssueLine(key: string): IssueDraftLine {
  return {
    key,
    inventoryItemId: "",
    sku: "",
    baseUom: "",
    quantity: "1",
    uom: "",
  };
}
export function copyIssueDraft(v: IssueDraftValues): IssueDraftValues {
  return { ...v, lines: v.lines.map((l) => ({ ...l })) };
}
export function normalizeIssueQuantity(value: string): string {
  return value.trim().replace(",", ".");
}
export function issuePayloadSignature(v: IssueDraftValues): string {
  return JSON.stringify({
    warehouseId: v.warehouseId,
    ownerId: v.ownerId,
    lines: v.lines.map((l) => ({
      inventoryItemId: l.inventoryItemId,
      quantity: normalizeIssueQuantity(l.quantity),
      uom: l.uom,
    })),
  });
}
export function validateIssueDraft(v: IssueDraftValues): IssueErrors {
  const e: IssueErrors = { lineFields: {} };
  if (!v.warehouseId) e.warehouseId = "Выберите склад.";
  if (!v.ownerId) e.ownerId = "Выберите компанию-владельца.";
  if (v.lines.length > 100) e.lines = "В документе допустимо до 100 строк.";
  for (const l of v.lines) {
    const f: IssueErrors["lineFields"][string] = {};
    if (!l.inventoryItemId) f.inventoryItemId = "Выберите SKU.";
    const q = normalizeIssueQuantity(l.quantity);
    if (q.length > 128 || !/^\d+(?:\.\d+)?$/.test(q) || !/[1-9]/.test(q))
      f.quantity = "Укажите положительное десятичное количество.";
    if (!l.uom) f.uom = "Выберите единицу.";
    if (Object.keys(f).length) e.lineFields[l.key] = f;
  }
  return e;
}
export function hasIssueErrors(e: IssueErrors): boolean {
  return (
    !!e.warehouseId ||
    !!e.ownerId ||
    !!e.lines ||
    Object.keys(e.lineFields).length > 0
  );
}
export class IssueCreationAttempt {
  private attempt: {
    key: string;
    signature: string;
    values: IssueDraftValues;
  } | null = null;
  uncertain = false;
  begin(
    values: IssueDraftValues,
    key: () => string,
  ): { key: string; values: IssueDraftValues } {
    const signature = issuePayloadSignature(values);
    if (this.uncertain && this.attempt && this.attempt.signature !== signature)
      throw new Error("Сначала повторите исходный запрос с тем же ключом.");
    if (!this.attempt || this.attempt.signature !== signature)
      this.attempt = {
        key: key(),
        signature,
        values: copyIssueDraft(values),
      };
    if (!this.uncertain) this.attempt.values = copyIssueDraft(values);
    return {
      key: this.attempt.key,
      values: copyIssueDraft(this.attempt.values),
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
