import type { InventoryScope } from "./inventory-scope.types";
import type { InternalMovesParams } from "./internal-move.types";
type Root = readonly [
  "inventory",
  ...InventoryScope,
  "stock-documents/internal-moves",
];
export const internalMoveKeys = {
  root: (scope: InventoryScope): Root =>
    ["inventory", ...scope, "stock-documents/internal-moves"] as const,
  lists: (scope: InventoryScope): readonly [...Root, "list"] =>
    [...internalMoveKeys.root(scope), "list"] as const,
  list: (
    scope: InventoryScope,
    p: InternalMovesParams,
  ): readonly [...Root, "list", InternalMovesParams] =>
    [...internalMoveKeys.lists(scope), { ...p }] as const,
  detail: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "detail", string] =>
    [...internalMoveKeys.root(scope), "detail", id] as const,
  update: (scope: InventoryScope): readonly [...Root, "update"] =>
    [...internalMoveKeys.root(scope), "update"] as const,
  confirm: (scope: InventoryScope): readonly [...Root, "confirm"] =>
    [...internalMoveKeys.root(scope), "confirm"] as const,
  cancel: (scope: InventoryScope): readonly [...Root, "cancel"] =>
    [...internalMoveKeys.root(scope), "cancel"] as const,
  create: (scope: InventoryScope): readonly [...Root, "create"] =>
    [...internalMoveKeys.root(scope), "create"] as const,
};
