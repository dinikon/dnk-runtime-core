import type {
  WarehouseCreateValues,
  WarehouseFieldErrors,
} from "./warehouse.types.ts";
export function validateWarehouse(
  values: WarehouseCreateValues,
): WarehouseFieldErrors {
  const errors: WarehouseFieldErrors = {};
  if (!values.code.trim()) errors.code = "Укажите код склада.";
  if (!values.name.trim()) errors.name = "Укажите название склада.";
  return errors;
}
