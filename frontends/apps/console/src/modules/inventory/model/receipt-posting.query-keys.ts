import type { InventoryScope } from "./inventory-scope.types";
import type { ReceiptReferencesParams } from "./receipt-posting.types";
type Root = readonly ["inventory", ...InventoryScope];
export const receiptPostingKeys = {
  context: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "receipt-context", string] =>
    ["inventory", ...scope, "receipt-context", id] as const,
  execution: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "execution", string] =>
    ["inventory", ...scope, "execution", id] as const,
  posting: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "posting", string] =>
    ["inventory", ...scope, "posting", id] as const,
  history: (
    scope: InventoryScope,
    id: string,
    offset: number,
  ): readonly [...Root, "receipt-history", string, number] =>
    ["inventory", ...scope, "receipt-history", id, offset] as const,
  references: (
    scope: InventoryScope,
    id: string,
    params: ReceiptReferencesParams,
  ): readonly [
    ...Root,
    "receipt-references",
    string,
    ReceiptReferencesParams,
  ] =>
    ["inventory", ...scope, "receipt-references", id, { ...params }] as const,
  post: (scope: InventoryScope): readonly [...Root, "post-receipt"] =>
    ["inventory", ...scope, "post-receipt"] as const,
};
