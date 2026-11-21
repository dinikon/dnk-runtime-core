import type {
  ReceiptPreparation,
  ReceiptPreparationLine,
  ReceiptIntakeGroup,
  ReceiptIntakeValues,
  ReceiptIntakeErrors,
  IntakeRow,
  IntakeReference,
  ReceiptReferenceKind,
} from "./receipt-posting.types.ts";
export { quantityText as intakeDecimal } from "./stock-quantity-text.ts";
import {
  quantityText as intakeDecimal,
  compareQuantities as compareIntakeQuantities,
  sumQuantities,
} from "./stock-quantity-text.ts";
export function serialTracking(row: IntakeRow): boolean {
  return row.trackingMode === "SERIAL" || row.trackingMode === "LOT_AND_SERIAL";
}
export function lotTracking(row: IntakeRow): boolean {
  return row.trackingMode === "LOT" || row.trackingMode === "LOT_AND_SERIAL";
}
export function prepareIntake(
  context: ReceiptPreparation,
  key: () => string,
): ReceiptIntakeValues {
  return {
    expectedVersion: context.version,
    rows: context.lines.map((line) => ({
      ...line,
      key: key(),
      selected: hasRemaining(line),
      quantity:
        line.trackingMode === "SERIAL" || line.trackingMode === "LOT_AND_SERIAL"
          ? "1"
          : intakeDecimal(line.remainingQuantity),
      uom: line.baseUom,
      locationId: context.defaultStorageLocationId ?? "",
      locationLabel: context.defaultStorageLocationId
        ? "Основная STORAGE-локация"
        : "",
      lotId: "",
      lotNumber: "",
      serialId: "",
      serialNumber: "",
      manufacturedOn: null,
      expiresOn: null,
      stockStatus: "SELLABLE",
      costKnown: false,
      costAmount: "",
      costCurrency: "",
      costReference: "",
    })),
    unallocatedCost: { known: false, amount: "", currency: "", reference: "" },
  };
}
export function copyIntake(values: ReceiptIntakeValues): ReceiptIntakeValues {
  return {
    ...values,
    rows: values.rows.map((row) => ({ ...row })),
    unallocatedCost: { ...values.unallocatedCost },
  };
}
export function duplicateIntakeRow(row: IntakeRow, key: string): IntakeRow {
  return {
    ...row,
    key,
    quantity: serialTracking(row) ? "1" : "",
    serialId: "",
    serialNumber: "",
    costKnown: false,
    costAmount: "",
    costCurrency: "",
    costReference: "",
  };
}
export function chooseIntakeReference(
  row: IntakeRow,
  kind: ReceiptReferenceKind,
  option: IntakeReference,
): IntakeRow {
  if (kind === "locations")
    return { ...row, locationId: option.id, locationLabel: option.label };
  if (kind === "lots")
    return {
      ...row,
      lotId: option.id,
      lotNumber: option.label,
      serialId: "",
      serialNumber: "",
      manufacturedOn: option.manufacturedOn,
      expiresOn: option.expiresOn,
    };
  return {
    ...row,
    serialId: option.id,
    serialNumber: option.label,
    lotId: option.lotId ?? "",
    lotNumber: option.lotNumber ?? "",
    manufacturedOn: option.manufacturedOn,
    expiresOn: option.expiresOn,
  };
}
export function intakeSignature(values: ReceiptIntakeValues): string {
  return JSON.stringify({
    version: values.expectedVersion,
    rows: values.rows.map((row) => ({
      key: row.key,
      selected: row.selected,
      line: row.documentLineId,
      quantity: intakeDecimal(row.quantity),
      uom: row.uom,
      location: row.locationId,
      lot: row.lotId,
      serial: row.serialId,
      status: row.stockStatus,
      cost: row.costKnown
        ? {
            amount: intakeDecimal(row.costAmount),
            currency: row.costCurrency.trim().toUpperCase(),
            reference: row.costReference.trim(),
          }
        : null,
    })),
    unallocated: values.unallocatedCost.known
      ? {
          amount: intakeDecimal(values.unallocatedCost.amount),
          currency: values.unallocatedCost.currency.trim().toUpperCase(),
          reference: values.unallocatedCost.reference.trim(),
        }
      : null,
  });
}
export function validateIntake(
  values: ReceiptIntakeValues,
): ReceiptIntakeErrors {
  const result: ReceiptIntakeErrors = { rows: {} };
  const rows = selectedIntakeRows(values);
  if (!rows.length || rows.length > 500)
    result.form = "Нужно от 1 до 500 фактических строк.";
  const serials = new Set<string>();
  const money = (amount: string, currency: string): boolean =>
    /^\d+(?:\.\d{1,4})?$/.test(intakeDecimal(amount)) &&
    /^[A-Za-z]{3}$/.test(currency.trim());
  for (const row of rows) {
    const q = intakeDecimal(row.quantity);
    let error = "";
    if (q.length > 128 || !/^\d+(?:\.\d+)?$/.test(q) || !/[1-9]/.test(q))
      error = "Укажите положительное количество.";
    else if (!hasRemaining(row))
      error = "Строка плана уже выполнена. Исключите её из приёмки.";
    else if (row.baseUom !== row.currentBaseUom)
      error = "Базовая единица SKU изменилась. Требуется актуальный план.";
    else if (!row.locationId) error = "Выберите локацию.";
    else if (lotTracking(row) && !row.lotId) error = "Выберите партию.";
    else if (
      serialTracking(row) &&
      (!row.serialId || q !== "1" || row.uom !== "PCS")
    )
      error = "Выберите экземпляр в количестве 1 PCS.";
    else if (serialTracking(row) && serials.has(row.serialId))
      error = "Экземпляр уже выбран в другой строке.";
    else if (row.expirationMode === "REQUIRED" && !row.expiresOn)
      error = "У партии не заполнен обязательный срок годности.";
    else if (row.costKnown && !money(row.costAmount, row.costCurrency))
      error = "Укажите известную сумму (до 4 знаков) и код валюты.";
    if (row.serialId) serials.add(row.serialId);
    if (error) result.rows[row.key] = error;
  }
  for (const group of intakeGroups(values)) {
    const selected = group.rows.filter((row) => row.selected);
    const total = intakeBaseTotal(selected);
    if (
      total !== null &&
      compareIntakeQuantities(total, group.line.remainingQuantity) > 0
    ) {
      result.lines ??= {};
      result.lines[group.line.documentLineId] =
        `Распределено ${total} ${group.line.baseUom}, осталось ${group.line.remainingQuantity} ${group.line.baseUom}. Уменьшите количество.`;
    }
  }
  if (
    values.unallocatedCost.known &&
    !money(values.unallocatedCost.amount, values.unallocatedCost.currency)
  )
    result.costs = "Проверьте общую нераспределённую сумму и валюту.";
  return result;
}
export class ReceiptIntakeAttempt {
  private sent: {
    key: string;
    signature: string;
    values: ReceiptIntakeValues;
  } | null = null;
  uncertain = false;
  begin(
    values: ReceiptIntakeValues,
    key: () => string,
  ): { key: string; values: ReceiptIntakeValues } {
    const signature = intakeSignature(values);
    if (this.uncertain && this.sent && signature !== this.sent.signature)
      throw new Error("Сначала повторите исходную команду приёмки.");
    if (!this.sent || this.sent.signature !== signature)
      this.sent = { key: key(), signature, values: copyIntake(values) };
    return { key: this.sent.key, values: copyIntake(this.sent.values) };
  }
  fail(uncertain: boolean): void {
    this.uncertain = uncertain;
  }
  clear(): void {
    this.sent = null;
    this.uncertain = false;
  }
}

export function hasRemaining(line: ReceiptPreparationLine): boolean {
  return /[1-9]/.test(line.remainingQuantity.split(/[eE]/)[0] ?? "");
}
export function selectedIntakeRows(values: ReceiptIntakeValues): IntakeRow[] {
  return values.rows.filter((row) => row.selected);
}
export function intakeGroups(
  values: ReceiptIntakeValues,
  context?: ReceiptPreparation,
): ReceiptIntakeGroup[] {
  const groups = new Map<string, ReceiptIntakeGroup>();
  for (const row of values.rows) {
    let group = groups.get(row.documentLineId);
    if (!group) {
      group = {
        line: row,
        current: context?.lines.find(
          (line) => line.documentLineId === row.documentLineId,
        ),
        rows: [],
      };
      groups.set(row.documentLineId, group);
    }
    group.rows.push(row);
  }
  return [...groups.values()].sort(
    (left, right) =>
      left.line.position - right.line.position ||
      left.line.documentLineId.localeCompare(right.line.documentLineId),
  );
}
export function selectIntakeLine(
  values: ReceiptIntakeValues,
  id: string,
  selected: boolean,
): ReceiptIntakeValues {
  return {
    ...values,
    rows: values.rows.map((row) =>
      row.documentLineId === id
        ? { ...row, selected: selected && hasRemaining(row) }
        : row,
    ),
  };
}
export function rebaseIntake(
  values: ReceiptIntakeValues,
  context: ReceiptPreparation,
): ReceiptIntakeValues {
  return {
    ...copyIntake(values),
    expectedVersion: context.version,
    rows: values.rows.map((row) => {
      const line = context.lines.find(
        (value) => value.documentLineId === row.documentLineId,
      );
      return line
        ? { ...row, ...line, selected: row.selected && hasRemaining(line) }
        : { ...row, selected: false, remainingQuantity: "0" };
    }),
  };
}
export function intakeBaseTotal(rows: readonly IntakeRow[]): string | null {
  if (rows.some((row) => row.uom !== row.baseUom)) return null;
  return sumQuantities(rows.map((row) => row.quantity));
}
