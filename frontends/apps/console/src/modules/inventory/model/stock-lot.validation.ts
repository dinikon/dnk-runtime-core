import type {
  StockLotValues,
  StockLotErrors,
  StockLotDatesValues,
  StockLotDatesErrors,
} from "./stock-lot.types.ts";
import type { InventoryTrackingMode } from "./inventory-item.types.ts";
export function allowsStockLots(mode: InventoryTrackingMode): boolean {
  return mode === "LOT" || mode === "LOT_AND_SERIAL";
}
export function validCalendarDate(value: string): boolean {
  const parts = /^([0-9]{4})-([0-9]{2})-([0-9]{2})$/.exec(value);
  if (!parts) return false;
  const year = Number(parts[1]),
    month = Number(parts[2]),
    day = Number(parts[3]);
  if (year < 1 || month < 1 || month > 12 || day < 1) return false;
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  return (
    day <=
    [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]!
  );
}
export function validateStockLot(
  values: StockLotValues,
  expirationMode: string,
): StockLotErrors {
  const errors: StockLotErrors = {};
  if (!values.number.trim() || /[\p{Cc}\p{Cf}]/u.test(values.number))
    errors.number = "Укажите номер партии без управляющих символов.";
  return { ...validateStockLotDates(values, expirationMode), ...errors };
}
export function validateStockLotDates(
  values: StockLotDatesValues,
  expirationMode: string,
): StockLotDatesErrors {
  const errors: StockLotDatesErrors = {};
  for (const key of ["manufacturedOn", "expiresOn"] as const)
    if (values[key] && !validCalendarDate(values[key]))
      errors[key] = "Укажите календарную дату ГГГГ-ММ-ДД.";
  if (expirationMode === "NONE" && values.expiresOn)
    errors.expiresOn = "Для этого SKU срок годности не заполняется.";
  if (
    !errors.manufacturedOn &&
    !errors.expiresOn &&
    values.manufacturedOn &&
    values.expiresOn &&
    values.manufacturedOn > values.expiresOn
  )
    errors.expiresOn = "Срок годности не может быть раньше даты производства.";
  return errors;
}
export function displayStockDate(value: string | null): string {
  if (!value) return "—";
  const [year, month, day] = value.split("-");
  return `${day}.${month}.${year}`;
}
