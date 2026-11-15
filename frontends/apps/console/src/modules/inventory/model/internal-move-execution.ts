import type {
  InternalMoveAllocation,
  InternalMovePreparation,
  InternalMoveExecutionValues,
  InternalMoveExecutionErrors,
} from "./internal-move-posting.types.ts";
import {
  quantityText,
  compareQuantities,
  sumQuantities,
} from "./stock-quantity-text.ts";
export function selectedInternalMoveRows(
  values: InternalMoveExecutionValues,
): InternalMoveAllocation[] {
  return values.rows.filter((v) => v.selected);
}
export function prepareInternalMoveExecution(
  context: InternalMovePreparation,
  key: () => string,
): InternalMoveExecutionValues {
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
      destination: null,
      destinationMissing: false,
    })),
  };
}
export function copyInternalMoveExecution(
  values: InternalMoveExecutionValues,
): InternalMoveExecutionValues {
  return {
    ...values,
    rows: values.rows.map((v) => ({
      ...v,
      source: v.source ? { ...v.source } : null,
      destination: v.destination ? { ...v.destination } : null,
    })),
  };
}
export function internalMoveExecutionSignature(
  values: InternalMoveExecutionValues,
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
      destination: v.destination?.id ?? null,
    })),
  });
}
export function splitInternalMoveAllocation(
  row: InternalMoveAllocation,
  key: string,
): InternalMoveAllocation {
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
export function rebaseInternalMoveExecution(
  values: InternalMoveExecutionValues,
  context: InternalMovePreparation,
): InternalMoveExecutionValues {
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
export function internalMoveBaseTotal(
  rows: readonly InternalMoveAllocation[],
): string | null {
  return rows.some((row) => row.uom !== row.baseUom)
    ? null
    : sumQuantities(rows.map((row) => row.quantity));
}
export function validateInternalMoveExecution(
  values: InternalMoveExecutionValues,
): InternalMoveExecutionErrors {
  const result: InternalMoveExecutionErrors = { rows: {}, lines: {} };
  const rows = selectedInternalMoveRows(values);
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
    else if (!row.destination || row.destinationMissing)
      message = "Выберите доступную локацию назначения.";
    else if (row.destination.id === row.source.locationId)
      message = "Источник и назначение должны иметь разные адреса.";
    else if (
      row.trackingMode.includes("SERIAL") &&
      (q !== "1" || row.uom !== "PCS")
    )
      message = "Один серийный экземпляр перемещениеуется в количестве 1 PCS.";
    if (message) result.rows[row.key] = message;
  }
  for (const id of new Set(rows.map((v) => v.documentLineId))) {
    const allocations = rows.filter((v) => v.documentLineId === id),
      line = allocations[0];
    const total = internalMoveBaseTotal(allocations);
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
    const total = internalMoveBaseTotal(allocations);
    if (
      source &&
      total !== null &&
      compareQuantities(total, source.onHandQuantity) > 0
    )
      for (const row of allocations)
        result.rows[row.key] =
          `Недостаточно физического количества. Выбрано ${total} ${source.baseUom}, по последним сведениям ${source.onHandQuantity}. Обновите сведения.`;
  }
  const dimensionsKey = (
    row: InternalMoveAllocation,
    location: string,
  ): string =>
    JSON.stringify([
      row.inventoryItemId,
      location,
      row.source?.lotId,
      row.source?.serialId,
      row.source?.stockStatus,
      row.baseUom,
    ]);
  const destinations = new Set(
    rows
      .filter((v) => v.source && v.destination)
      .map((v) => dimensionsKey(v, v.destination!.id)),
  );
  const serials = rows.map((v) => v.source?.serialId).filter((v) => !!v);
  for (const row of rows) {
    if (
      row.source &&
      destinations.has(dimensionsKey(row, row.source.locationId))
    )
      result.rows[row.key] =
        "Одна позиция участвует в приходе и расходе. Выполните маршруты отдельными исполнениями.";
    if (
      row.source?.serialId &&
      serials.filter((v) => v === row.source!.serialId).length > 1
    )
      result.rows[row.key] =
        "Экземпляр может участвовать в исполнении только один раз.";
  }
  return result;
}
export function hasInternalMoveExecutionErrors(
  errors: InternalMoveExecutionErrors,
): boolean {
  return (
    !!errors.form ||
    !!Object.keys(errors.rows).length ||
    !!Object.keys(errors.lines).length
  );
}
export class InternalMoveExecutionAttempt {
  private sent: {
    key: string;
    signature: string;
    values: InternalMoveExecutionValues;
  } | null = null;
  uncertain = false;
  begin(
    values: InternalMoveExecutionValues,
    key: () => string,
  ): { key: string; values: InternalMoveExecutionValues } {
    const signature = internalMoveExecutionSignature(values);
    if (this.uncertain && this.sent && signature !== this.sent.signature)
      throw new Error("Сначала повторите исходную команду перемещения.");
    if (!this.sent || this.sent.signature !== signature)
      this.sent = {
        key: key(),
        signature,
        values: copyInternalMoveExecution(values),
      };
    return {
      key: this.sent.key,
      values: copyInternalMoveExecution(this.sent.values),
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
