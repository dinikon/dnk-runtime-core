import type {
  StatusChangeAllocation,
  StatusChangePreparation,
  StatusChangeExecutionValues,
  StatusChangeExecutionErrors,
} from "./status-change-posting.types.ts";
import {
  quantityText,
  compareQuantities,
  sumQuantities,
} from "./stock-quantity-text.ts";
export function selectedStatusChangeRows(
  values: StatusChangeExecutionValues,
): StatusChangeAllocation[] {
  return values.rows.filter((v) => v.selected);
}
export function prepareStatusChangeExecution(
  context: StatusChangePreparation,
  key: () => string,
): StatusChangeExecutionValues {
  return {
    expectedVersion: context.version,
    rows: context.lines.map((line) => ({
      ...line,
      key: key(),
      selected: /[1-9]/.test(line.remainingQuantity.split(/[eE]/)[0] ?? ""),
      quantity: line.trackingMode.includes("SERIAL")
        ? "1"
        : quantityText(line.remainingQuantity),
      uom: line.baseUom,
      source: null,
      sourceMissing: false,
    })),
  };
}
export function copyStatusChangeExecution(
  values: StatusChangeExecutionValues,
): StatusChangeExecutionValues {
  return {
    ...values,
    rows: values.rows.map((v) => ({
      ...v,
      source: v.source ? { ...v.source } : null,
    })),
  };
}
export function statusChangeExecutionSignature(
  values: StatusChangeExecutionValues,
): string {
  return JSON.stringify({
    version: values.expectedVersion,
    rows: values.rows.map((v) => ({
      key: v.key,
      line: v.documentLineId,
      selected: v.selected,
      quantity: quantityText(v.quantity),
      uom: v.uom,
      source: v.source?.id ?? null,
    })),
  });
}
export function splitStatusChangeAllocation(
  row: StatusChangeAllocation,
  key: string,
): StatusChangeAllocation {
  return {
    ...row,
    key,
    quantity: row.trackingMode.includes("SERIAL") ? "1" : "",
    source: row.trackingMode.includes("SERIAL")
      ? null
      : row.source
        ? { ...row.source }
        : null,
    sourceMissing: false,
  };
}
export function rebaseStatusChangeExecution(
  values: StatusChangeExecutionValues,
  context: StatusChangePreparation,
): StatusChangeExecutionValues {
  return {
    expectedVersion: context.version,
    rows: values.rows.map((row) => {
      const line = context.lines.find(
        (v) => v.documentLineId === row.documentLineId,
      );
      return line
        ? {
            ...row,
            ...line,
            source: row.source ? { ...row.source } : null,
            selected:
              row.selected &&
              /[1-9]/.test(line.remainingQuantity.split(/[eE]/)[0] ?? ""),
          }
        : { ...row, selected: false };
    }),
  };
}
export function statusChangeBaseTotal(
  rows: readonly StatusChangeAllocation[],
): string | null {
  return rows.some((row) => row.uom !== row.baseUom)
    ? null
    : sumQuantities(rows.map((row) => row.quantity));
}
export function validateStatusChangeExecution(
  values: StatusChangeExecutionValues,
): StatusChangeExecutionErrors {
  const result: StatusChangeExecutionErrors = { rows: {}, lines: {} };
  const rows = selectedStatusChangeRows(values);
  if (!rows.length || rows.length > 500)
    result.form = "Выберите от 1 до 500 фактических распределений.";
  for (const row of rows) {
    const q = quantityText(row.quantity);
    let message = "";
    if (q.length > 128 || !/^\d+(?:\.\d+)?$/.test(q) || !/[1-9]/.test(q))
      message = "Укажите положительное количество.";
    else if (row.baseUom !== row.currentBaseUom)
      message = "Базовая единица SKU изменилась. Обновите основание.";
    else if (!row.source || row.sourceMissing)
      message = "Выберите существующую исходную позицию.";
    else if (
      row.trackingMode.includes("SERIAL") &&
      (q !== "1" || row.uom !== "PCS")
    )
      message =
        "Состояние одного серийного экземпляра меняется в количестве 1 PCS.";
    if (message) result.rows[row.key] = message;
  }
  for (const id of new Set(rows.map((v) => v.documentLineId))) {
    const allocations = rows.filter((v) => v.documentLineId === id),
      line = allocations[0];
    const total = statusChangeBaseTotal(allocations);
    if (
      line &&
      total !== null &&
      compareQuantities(total, line.remainingQuantity) > 0
    )
      result.lines[id] =
        `Распределено ${total} ${line.baseUom}, осталось по плану ${line.remainingQuantity}.`;
  }
  for (const id of new Set(
    rows.map((v) => v.source?.id).filter((v) => v !== undefined),
  )) {
    const allocations = rows.filter((v) => v.source?.id === id),
      source = allocations[0]?.source;
    const total = statusChangeBaseTotal(allocations);
    if (
      source &&
      total !== null &&
      compareQuantities(total, source.onHandQuantity) > 0
    )
      for (const row of allocations)
        result.rows[row.key] =
          `Недостаточно физического количества. Выбрано ${total} ${source.baseUom}, по последним сведениям ${source.onHandQuantity}. Обновите сведения.`;
  }
  return result;
}
export function hasStatusChangeExecutionErrors(
  errors: StatusChangeExecutionErrors,
): boolean {
  return (
    !!errors.form ||
    !!Object.keys(errors.rows).length ||
    !!Object.keys(errors.lines).length
  );
}
export class StatusChangeExecutionAttempt {
  private sent: {
    key: string;
    signature: string;
    values: StatusChangeExecutionValues;
  } | null = null;
  uncertain = false;
  begin(
    values: StatusChangeExecutionValues,
    key: () => string,
  ): { key: string; values: StatusChangeExecutionValues } {
    const signature = statusChangeExecutionSignature(values);
    if (this.uncertain && this.sent && signature !== this.sent.signature)
      throw new Error(
        "Сначала повторите исходную команду изменения состояния.",
      );
    if (!this.sent || this.sent.signature !== signature)
      this.sent = {
        key: key(),
        signature,
        values: copyStatusChangeExecution(values),
      };
    return {
      key: this.sent.key,
      values: copyStatusChangeExecution(this.sent.values),
    };
  }
  fail(uncertain: boolean): void {
    this.uncertain = uncertain;
  }
  clear(): void {
    this.sent = null;
    this.uncertain = false;
  }
}
