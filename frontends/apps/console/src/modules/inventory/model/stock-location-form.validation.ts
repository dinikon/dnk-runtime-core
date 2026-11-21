import type {
  StockLocationEditValues,
  StockLocationCreateFormValues,
  StockLocationFieldErrors,
} from "./stock-location.types.ts";
import { isStockLocationType } from "./stock-location.constants.ts";
export function validateStockLocation(
  value: Pick<StockLocationEditValues, "code" | "name">,
): StockLocationFieldErrors {
  const errors: StockLocationFieldErrors = {};
  if (!value.code.trim()) errors.code = "Укажите код локации.";
  if (!value.name.trim()) errors.name = "Укажите название локации.";
  return errors;
}
export function validateStockLocationCreate(
  value: StockLocationCreateFormValues,
): StockLocationFieldErrors {
  const errors = validateStockLocation(value);
  if (!isStockLocationType(value.locationType))
    errors.locationType = "Выберите тип локации.";
  return errors;
}
