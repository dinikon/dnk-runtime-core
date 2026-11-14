import type { InventoryScope } from "./inventory-scope.types.ts";
import type { StockSerialsListParams } from "./stock-serial.types.ts";
type Root = readonly ["inventory", ...InventoryScope, "serials", string];
export const stockSerialKeys = {
  root: (scope: InventoryScope, itemId: string): Root =>
    ["inventory", ...scope, "serials", itemId] as const,
  lists: (scope: InventoryScope, itemId: string): readonly [...Root, "list"] =>
    [...stockSerialKeys.root(scope, itemId), "list"] as const,
  list: (
    scope: InventoryScope,
    itemId: string,
    params: StockSerialsListParams,
  ): readonly [...Root, "list", StockSerialsListParams] =>
    [...stockSerialKeys.lists(scope, itemId), params] as const,
  detail: (
    scope: InventoryScope,
    itemId: string,
    serialId: string,
  ): readonly [...Root, "detail", string] =>
    [...stockSerialKeys.root(scope, itemId), "detail", serialId] as const,
  update: (
    scope: InventoryScope,
    itemId: string,
    serialId: string,
  ): readonly [...Root, "update", string] =>
    [...stockSerialKeys.root(scope, itemId), "update", serialId] as const,
  create: (
    scope: InventoryScope,
    itemId: string,
  ): readonly [...Root, "create"] =>
    [...stockSerialKeys.root(scope, itemId), "create"] as const,
};
