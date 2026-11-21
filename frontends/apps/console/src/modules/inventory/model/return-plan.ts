import type { ReturnOriginLine } from "./return-origin.types";
import type { ReturnDraftLine } from "./return.types";
import { quantityText } from "./stock-quantity-text.ts";
export function returnPlanLine(
  origin: ReturnOriginLine,
  key: string,
): ReturnDraftLine {
  return {
    key,
    originExecutionLineId: origin.id,
    inventoryItemId: origin.inventoryItemId,
    sku: origin.sku,
    baseUom: origin.baseUom,
    quantity: quantityText(origin.remainingQuantity),
    uom: origin.baseUom,
  };
}
export function toggleReturnOrigin(
  lines: readonly ReturnDraftLine[],
  origin: ReturnOriginLine,
  selected: boolean,
  key: () => string,
): ReturnDraftLine[] {
  const current = lines.find((v) => v.originExecutionLineId === origin.id);
  if (selected && !current) return [...lines, returnPlanLine(origin, key())];
  return selected
    ? [...lines]
    : lines.filter((v) => v.originExecutionLineId !== origin.id);
}
