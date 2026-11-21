import type { InventoryScope } from "./inventory-scope.types";
import type { ReceiptsParams } from "./receipt.types";
type Root = readonly ["inventory", ...InventoryScope, "stock-documents"];
export const receiptKeys = {
  root: (scope: InventoryScope): Root =>
    ["inventory", ...scope, "stock-documents"] as const,
  lists: (scope: InventoryScope): readonly [...Root, "list"] =>
    [...receiptKeys.root(scope), "list"] as const,
  list: (
    scope: InventoryScope,
    p: ReceiptsParams,
  ): readonly [...Root, "list", ReceiptsParams] =>
    [...receiptKeys.lists(scope), { ...p }] as const,
  detail: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "detail", string] =>
    [...receiptKeys.root(scope), "detail", id] as const,
  update: (scope: InventoryScope): readonly [...Root, "update"] =>
    [...receiptKeys.root(scope), "update"] as const,
  confirm: (scope: InventoryScope): readonly [...Root, "confirm"] =>
    [...receiptKeys.root(scope), "confirm"] as const,
  cancel: (scope: InventoryScope): readonly [...Root, "cancel"] =>
    [...receiptKeys.root(scope), "cancel"] as const,
  create: (scope: InventoryScope): readonly [...Root, "create"] =>
    [...receiptKeys.root(scope), "create"] as const,
};
