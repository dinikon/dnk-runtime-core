export interface ReturnOriginLine {
  id: string;
  position: number;
  inventoryItemId: string;
  sku: string;
  baseUom: string;
  quantity: string;
  returnedQuantity: string;
  remainingQuantity: string;
  locationId: string;
  locationCode: string;
  stockStatus: string;
  lotId: string | null;
  lotNumber: string | null;
  serialId: string | null;
  serialNumber: string | null;
}
export interface ReturnOrigin {
  executionId: string;
  documentId: string;
  operationType: string;
  direction: string;
  warehouseId: string;
  warehouseCode: string;
  warehouseName: string;
  ownerId: string;
  lines: ReturnOriginLine[];
}
export function returnDirectionLabel(value: string): string {
  return value === "FROM_RECIPIENT"
    ? "Возврат от получателя"
    : value === "TO_SUPPLIER"
      ? "Возврат поставщику"
      : value;
}
