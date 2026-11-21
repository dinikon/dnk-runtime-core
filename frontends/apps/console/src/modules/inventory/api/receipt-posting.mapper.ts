import type {
  PostReceiptResponseDTO,
  GetStockExecutionResponseDTO,
  GetStockPostingResponseDTO,
  PostReceiptRequestDTO,
  PrepareReceiptResponseDTO,
  ListReceiptReferencesResponseDTO,
  ListReceiptExecutionsResponseDTO,
} from "./receipt-posting.dto";
import type {
  ReceiptPostingResult,
  ReceiptPreparation,
  ReceiptIntakeValues,
  IntakeReferencesPage,
  ReceiptExecutionHistory,
} from "../model/receipt-posting.types";
import { intakeDecimal, selectedIntakeRows } from "../model/receipt-intake.ts";
export function postingResultFromDto(
  dto:
    | PostReceiptResponseDTO
    | GetStockExecutionResponseDTO
    | GetStockPostingResponseDTO,
): ReceiptPostingResult {
  return {
    documentId: dto.document_id,
    documentVersionBefore: dto.document_version_before,
    documentVersionAfter: dto.document_version_after,
    documentStatus: dto.document_status,
    executionId: dto.execution_id,
    postingId: dto.posting_id,
    eventId: dto.event_id,
    actorId: dto.actor_id,
    warehouseId: dto.warehouse_id,
    warehouseCode: dto.warehouse_code,
    warehouseName: dto.warehouse_name,
    ownerId: dto.owner_id,
    ownerName: dto.owner_name,
    postedAt: dto.posted_at,
    lines: dto.lines.map((value) => ({
      id: value.id,
      clientLineId: value.client_line_id,
      documentLineId: value.document_line_id,
      inventoryItemId: value.inventory_item_id,
      sku: value.sku,
      baseUom: value.base_uom,
      quantity: value.quantity,
      sourceQuantity: value.source_quantity,
      sourceUom: value.source_uom,
      factorToBase: value.factor_to_base,
      locationId: value.location_id,
      locationCode: value.location_code,
      lotId: value.lot_id,
      lotNumber: value.lot_number,
      serialId: value.serial_id,
      serialNumber: value.serial_number,
      stockStatus: value.stock_status,
      positionId: value.position_id,
      ledgerEntryId: value.ledger_entry_id,
    })),
    positions: dto.positions.map((value) => ({
      id: value.id,
      baseUom: value.base_uom,
      beforeQuantity: value.before_quantity,
      delta: value.delta,
      afterQuantity: value.after_quantity,
      beforeVersion: value.before_version,
      afterVersion: value.after_version,
    })),
    ledger: dto.ledger.map((value) => ({
      id: value.id,
      positionId: value.position_id,
      quantityDelta: value.quantity_delta,
      baseUom: value.base_uom,
    })),
    costs: dto.costs.map((value) => ({
      id: value.id,
      amount: value.amount,
      currency: value.currency,
      basisKind: value.basis_kind,
      sourceSystem: value.source_system,
      sourceReference: value.source_reference,
      allocations: value.allocations.map((a) => ({
        executionLineId: a.execution_line_id,
        amount: a.amount,
      })),
    })),
  };
}

export function preparationFromDto(
  dto: PrepareReceiptResponseDTO,
): ReceiptPreparation {
  return {
    documentId: dto.document_id,
    version: dto.version,
    status: dto.status,
    warehouseId: dto.warehouse_id,
    defaultStorageLocationId: dto.default_storage_location_id,
    lines: dto.lines.map((line) => ({
      documentLineId: line.document_line_id,
      inventoryItemId: line.inventory_item_id,
      sku: line.sku,
      baseUom: line.base_uom,
      currentBaseUom: line.current_base_uom,
      position: line.position,
      plannedQuantity: line.planned_quantity,
      executedQuantity: line.executed_quantity,
      remainingQuantity: line.remaining_quantity,
      quantityStep: line.quantity_step,
      trackingMode: line.tracking_mode,
      expirationMode: line.expiration_mode,
    })),
  };
}
export function intakeToDto(
  values: ReceiptIntakeValues,
): PostReceiptRequestDTO {
  const rows = selectedIntakeRows(values);
  const costs: PostReceiptRequestDTO["costs"] = rows
    .filter((row) => row.costKnown)
    .map((row) => ({
      amount: intakeDecimal(row.costAmount),
      currency: row.costCurrency.trim().toUpperCase(),
      basis_kind: "MANUAL",
      source_system: null,
      source_reference: row.costReference.trim() || null,
      allocations: [
        { client_line_id: row.key, amount: intakeDecimal(row.costAmount) },
      ],
    }));
  if (values.unallocatedCost.known)
    costs.push({
      amount: intakeDecimal(values.unallocatedCost.amount),
      currency: values.unallocatedCost.currency.trim().toUpperCase(),
      basis_kind: "MANUAL",
      source_system: null,
      source_reference: values.unallocatedCost.reference.trim() || null,
      allocations: [],
    });
  return {
    expected_version: values.expectedVersion,
    lines: rows.map((row) => ({
      client_line_id: row.key,
      document_line_id: row.documentLineId,
      quantity: intakeDecimal(row.quantity),
      uom: row.uom,
      location_id: row.locationId,
      lot_id: row.lotId || null,
      serial_id: row.serialId || null,
      stock_status: row.stockStatus,
    })),
    costs,
  };
}
export function referencesFromDto(
  dto: ListReceiptReferencesResponseDTO,
): IntakeReferencesPage {
  return {
    ...dto,
    items: dto.items.map((v) => ({
      id: v.id,
      label: v.label,
      lotId: v.lot_id,
      lotNumber: v.lot_number,
      manufacturedOn: v.manufactured_on,
      expiresOn: v.expires_on,
    })),
  };
}
export function executionHistoryFromDto(
  dto: ListReceiptExecutionsResponseDTO,
): ReceiptExecutionHistory {
  return {
    ...dto,
    items: dto.items.map((v) => ({
      executionId: v.execution_id,
      postingId: v.posting_id,
      postedAt: v.posted_at,
      documentVersionAfter: v.document_version_after,
      documentStatus: v.document_status,
      lineCount: v.line_count,
      lines: v.lines.map((line) => ({
        documentLineId: line.document_line_id,
        position: line.position,
        sku: line.sku,
        baseUom: line.base_uom,
        quantity: line.quantity,
        allocationCount: line.allocation_count,
      })),
    })),
  };
}
