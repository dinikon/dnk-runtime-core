import type { ReturnDraftValues, ReturnErrors } from "./return.types.ts";
export function emptyReturnDraft(): ReturnDraftValues {
  return { originExecutionId: "", reason: "", lines: [] };
}
export function copyReturnDraft(v: ReturnDraftValues): ReturnDraftValues {
  return { ...v, lines: v.lines.map((l) => ({ ...l })) };
}
export function normalizeReturnQuantity(value: string): string {
  return value.trim().replace(",", ".");
}
export function returnPayloadSignature(v: ReturnDraftValues): string {
  return JSON.stringify({
    originExecutionId: v.originExecutionId,
    reason: v.reason.trim(),
    lines: v.lines.map((l) => ({
      originExecutionLineId: l.originExecutionLineId,
      quantity: normalizeReturnQuantity(l.quantity),
      uom: l.uom,
    })),
  });
}
export function validateReturnPlan(
  v: Pick<ReturnDraftValues, "reason" | "lines">,
): ReturnErrors {
  const e: ReturnErrors = { lineFields: {} };
  if (!v.reason.trim() || v.reason.trim().length > 1000)
    e.reason = "Укажите причину возврата от 1 до 1000 символов.";
  if (v.lines.length > 100) e.lines = "В документе допустимо до 100 строк.";
  for (const l of v.lines) {
    const f: ReturnErrors["lineFields"][string] = {};
    if (!l.originExecutionLineId)
      f.inventoryItemId = "Выберите строку исходного исполнения.";
    const q = normalizeReturnQuantity(l.quantity);
    if (q.length > 128 || !/^\d+(?:\.\d+)?$/.test(q) || !/[1-9]/.test(q))
      f.quantity = "Укажите положительное десятичное количество.";
    if (!l.uom) f.uom = "Выберите единицу.";
    if (Object.keys(f).length) e.lineFields[l.key] = f;
  }
  return e;
}
export function validateReturnDraft(v: ReturnDraftValues): ReturnErrors {
  const errors = validateReturnPlan(v);
  if (!v.originExecutionId)
    errors.originExecutionId = "Откройте возврат из исходного исполнения.";
  return errors;
}
export function hasReturnErrors(e: ReturnErrors): boolean {
  return (
    !!e.reason ||
    !!e.originExecutionId ||
    !!e.warehouseId ||
    !!e.ownerId ||
    !!e.lines ||
    Object.keys(e.lineFields).length > 0
  );
}
export class ReturnCreationAttempt {
  private attempt: {
    key: string;
    signature: string;
    values: ReturnDraftValues;
  } | null = null;
  uncertain = false;
  begin(
    values: ReturnDraftValues,
    key: () => string,
  ): { key: string; values: ReturnDraftValues } {
    const signature = returnPayloadSignature(values);
    if (this.uncertain && this.attempt && this.attempt.signature !== signature)
      throw new Error("Сначала повторите исходный запрос с тем же ключом.");
    if (!this.attempt || this.attempt.signature !== signature)
      this.attempt = {
        key: key(),
        signature,
        values: copyReturnDraft(values),
      };
    if (!this.uncertain) this.attempt.values = copyReturnDraft(values);
    return {
      key: this.attempt.key,
      values: copyReturnDraft(this.attempt.values),
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
