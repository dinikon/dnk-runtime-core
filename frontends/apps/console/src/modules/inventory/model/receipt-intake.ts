import type {
  ReceiptPreparation,
  ReceiptIntakeValues,
  ReceiptIntakeErrors,
  IntakeRow,
  IntakeReference,
  ReceiptReferenceKind,
} from "./receipt-posting.types.ts";
export function intakeDecimal(value: string): string {
  return value.trim().replace(",", ".");
}
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
    rows: context.lines
      .filter((line) => /[1-9]/.test(line.remainingQuantity))
      .map((line) => ({
        ...line,
        key: key(),
        quantity:
          line.trackingMode === "SERIAL" ||
          line.trackingMode === "LOT_AND_SERIAL"
            ? "1"
            : line.remainingQuantity,
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
  if (!values.rows.length || values.rows.length > 500)
    result.form = "Нужно от 1 до 500 фактических строк.";
  const serials = new Set<string>();
  const money = (amount: string, currency: string): boolean =>
    /^\d+(?:\.\d{1,4})?$/.test(intakeDecimal(amount)) &&
    /^[A-Za-z]{3}$/.test(currency.trim());
  for (const row of values.rows) {
    const q = intakeDecimal(row.quantity);
    let error = "";
    if (q.length > 128 || !/^\d+(?:\.\d+)?$/.test(q) || !/[1-9]/.test(q))
      error = "Укажите положительное количество.";
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
