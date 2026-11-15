import type { InventoryScope } from "./inventory-scope.types";
import type { StatusChangesParams } from "./status-change.types";
type Root = readonly [
  "inventory",
  ...InventoryScope,
  "stock-documents/status-changes",
];
export const statusChangeKeys = {
  root: (scope: InventoryScope): Root =>
    ["inventory", ...scope, "stock-documents/status-changes"] as const,
  lists: (scope: InventoryScope): readonly [...Root, "list"] =>
    [...statusChangeKeys.root(scope), "list"] as const,
  list: (
    scope: InventoryScope,
    p: StatusChangesParams,
  ): readonly [...Root, "list", StatusChangesParams] =>
    [...statusChangeKeys.lists(scope), { ...p }] as const,
  detail: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "detail", string] =>
    [...statusChangeKeys.root(scope), "detail", id] as const,
  update: (scope: InventoryScope): readonly [...Root, "update"] =>
    [...statusChangeKeys.root(scope), "update"] as const,
  confirm: (scope: InventoryScope): readonly [...Root, "confirm"] =>
    [...statusChangeKeys.root(scope), "confirm"] as const,
  cancel: (scope: InventoryScope): readonly [...Root, "cancel"] =>
    [...statusChangeKeys.root(scope), "cancel"] as const,
  create: (scope: InventoryScope): readonly [...Root, "create"] =>
    [...statusChangeKeys.root(scope), "create"] as const,
};
