import type {
  InventoryItemSettings,
  InventorySettingsErrors,
  InventoryUom,
} from "./inventory-item-settings.types.ts";

// Compare decimal coefficients and powers exactly, including API exponent notation.
function decimalStep(value: string): { positive: boolean; one: boolean } {
  const match = /^\+?(\d+(?:\.\d*)?|\.\d+)(?:[eE]([+-]?\d+))?$/.exec(
    value.trim(),
  );
  if (!match) return { positive: false, one: false };
  const coefficient = match[1]!,
    fraction = coefficient.split(".")[1] ?? "";
  const digits = coefficient.replace(".", "").replace(/^0+/, "");
  if (!digits) return { positive: false, one: false };
  const significant = digits.replace(/0+$/, "");
  const power =
    BigInt(match[2] ?? "0") -
    BigInt(fraction.length) +
    BigInt(digits.length - significant.length);
  return { positive: true, one: significant === "1" && power === 0n };
}

export function validateInventorySettings(
  value: InventoryItemSettings,
  uoms: readonly InventoryUom[],
): InventorySettingsErrors {
  const errors: InventorySettingsErrors = {};
  const step = decimalStep(value.quantityStep);
  if (!uoms.some((uom) => uom.code === value.baseUom))
    errors.baseUom = "Выберите единицу измерения из справочника.";
  if (!step.positive)
    errors.quantityStep = "Укажите положительный конечный шаг, например 0.001.";
  if (
    value.trackingMode === "SERIAL" ||
    value.trackingMode === "LOT_AND_SERIAL"
  ) {
    if (value.baseUom !== "PCS")
      errors.baseUom = "Серийный учёт требует единицу PCS.";
    if (!step.one) errors.quantityStep = "Серийный учёт требует шаг ровно 1.";
  }
  if (value.expirationMode === "REQUIRED" && value.trackingMode === "NONE")
    errors.expirationMode = "Обязательный срок требует учёта партий или серий.";
  return errors;
}
