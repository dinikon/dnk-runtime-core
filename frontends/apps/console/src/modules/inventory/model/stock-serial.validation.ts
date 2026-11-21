import type {
  StockSerialValues,
  StockSerialErrors,
} from "./stock-serial.types.ts";
import type { InventoryTrackingMode } from "./inventory-item.types.ts";
export function allowsStockSerials(mode: InventoryTrackingMode): boolean {
  return mode === "SERIAL" || mode === "LOT_AND_SERIAL";
}
export function validateStockSerial(
  values: StockSerialValues,
  mode: InventoryTrackingMode,
): StockSerialErrors {
  const errors: StockSerialErrors = {};
  if (!values.number.trim() || /[\p{Cc}\p{Cf}]/u.test(values.number))
    errors.number = "Укажите серийный номер без управляющих символов.";
  if (mode === "LOT_AND_SERIAL" && !values.lotId)
    errors.lotId = "Выберите партию этого SKU.";
  if (mode === "SERIAL" && values.lotId)
    errors.lotId =
      "В режиме SERIAL партия не используется. Очистите выбор партии.";
  return errors;
}
