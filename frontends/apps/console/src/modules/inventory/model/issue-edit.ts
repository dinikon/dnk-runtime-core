import type {
  IssueDocument,
  IssueEditValues,
  IssueDraftLine,
  IssueErrors,
} from "./issue.types.ts";
import { normalizeIssueQuantity, validateIssueDraft } from "./issue-draft.ts";
export function issueEditValues(document: IssueDocument): IssueEditValues {
  return {
    expectedVersion: document.version,
    lines: document.lines.map((line) => ({
      key: line.id,
      id: line.id,
      inventoryItemId: line.inventoryItemId,
      sku: line.sku,
      baseUom: line.baseUom,
      quantity: line.sourceQuantity,
      uom: line.sourceUom,
    })),
  };
}
export function copyIssueEdit(values: IssueEditValues): IssueEditValues {
  return {
    expectedVersion: values.expectedVersion,
    lines: values.lines.map((line) => ({ ...line })),
  };
}
export function issueEditSignature(values: IssueEditValues): string {
  return JSON.stringify({
    expectedVersion: values.expectedVersion,
    lines: values.lines.map((line) => ({
      id: line.id,
      inventoryItemId: line.id ? undefined : line.inventoryItemId,
      quantity: normalizeIssueQuantity(line.quantity),
      uom: line.uom,
    })),
  });
}
export function validateIssueEdit(values: IssueEditValues): IssueErrors {
  return validateIssueDraft({
    warehouseId: "selected",
    warehouseName: "",
    ownerId: "selected",
    ownerName: "",
    lines: values.lines,
  });
}
export function replaceIssueLine(
  values: IssueEditValues,
  key: string,
  value: IssueDraftLine,
): IssueEditValues {
  return {
    ...values,
    lines: values.lines.map((line) =>
      line.key === key
        ? {
            ...value,
            id: line.id,
            inventoryItemId: line.id
              ? line.inventoryItemId
              : value.inventoryItemId,
            sku: line.id ? line.sku : value.sku,
            baseUom: line.id ? line.baseUom : value.baseUom,
          }
        : line,
    ),
  };
}
export function newestIssue(
  current: IssueDocument | undefined,
  incoming: IssueDocument,
): IssueDocument {
  return current && current.version > incoming.version ? current : incoming;
}
