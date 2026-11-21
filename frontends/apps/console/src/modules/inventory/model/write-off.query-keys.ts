import type { InventoryScope } from "./inventory-scope.types";
import type { WriteOffsParams } from "./write-off.types";
type Root = readonly [
  "inventory",
  ...InventoryScope,
  "stock-documents/write-offs",
];
export const writeOffKeys = {
  root: (scope: InventoryScope): Root =>
    ["inventory", ...scope, "stock-documents/write-offs"] as const,
  lists: (scope: InventoryScope): readonly [...Root, "list"] =>
    [...writeOffKeys.root(scope), "list"] as const,
  list: (
    scope: InventoryScope,
    p: WriteOffsParams,
  ): readonly [...Root, "list", WriteOffsParams] =>
    [...writeOffKeys.lists(scope), { ...p }] as const,
  detail: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "detail", string] =>
    [...writeOffKeys.root(scope), "detail", id] as const,
  update: (scope: InventoryScope): readonly [...Root, "update"] =>
    [...writeOffKeys.root(scope), "update"] as const,
  confirm: (scope: InventoryScope): readonly [...Root, "confirm"] =>
    [...writeOffKeys.root(scope), "confirm"] as const,
  cancel: (scope: InventoryScope): readonly [...Root, "cancel"] =>
    [...writeOffKeys.root(scope), "cancel"] as const,
  create: (scope: InventoryScope): readonly [...Root, "create"] =>
    [...writeOffKeys.root(scope), "create"] as const,
};
