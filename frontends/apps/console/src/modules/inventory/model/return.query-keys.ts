import type { InventoryScope } from "./inventory-scope.types";
import type { ReturnsParams } from "./return.types";
type Root = readonly [
  "inventory",
  ...InventoryScope,
  "stock-documents/returns",
];
export const returnKeys = {
  root: (scope: InventoryScope): Root =>
    ["inventory", ...scope, "stock-documents/returns"] as const,
  origin: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "origin", string] =>
    [...returnKeys.root(scope), "origin", id] as const,
  lists: (scope: InventoryScope): readonly [...Root, "list"] =>
    [...returnKeys.root(scope), "list"] as const,
  list: (
    scope: InventoryScope,
    p: ReturnsParams,
  ): readonly [...Root, "list", ReturnsParams] =>
    [...returnKeys.lists(scope), { ...p }] as const,
  detail: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "detail", string] =>
    [...returnKeys.root(scope), "detail", id] as const,
  update: (scope: InventoryScope): readonly [...Root, "update"] =>
    [...returnKeys.root(scope), "update"] as const,
  confirm: (scope: InventoryScope): readonly [...Root, "confirm"] =>
    [...returnKeys.root(scope), "confirm"] as const,
  cancel: (scope: InventoryScope): readonly [...Root, "cancel"] =>
    [...returnKeys.root(scope), "cancel"] as const,
  create: (scope: InventoryScope): readonly [...Root, "create"] =>
    [...returnKeys.root(scope), "create"] as const,
};
