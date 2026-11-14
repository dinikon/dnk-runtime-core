import type { InventoryScope } from "./inventory-scope.types.ts";
import type { StockLotsListParams } from "./stock-lot.types.ts";
type Root = readonly ["inventory", ...InventoryScope, "lots", string];
export const stockLotKeys = {
  root: (scope: InventoryScope, itemId: string): Root =>
    ["inventory", ...scope, "lots", itemId] as const,
  candidates: (
    scope: InventoryScope,
    itemId: string,
    search: string,
  ): readonly [...Root, "candidates", string] =>
    [...stockLotKeys.root(scope, itemId), "candidates", search] as const,
  lists: (scope: InventoryScope, itemId: string): readonly [...Root, "list"] =>
    [...stockLotKeys.root(scope, itemId), "list"] as const,
  list: (
    scope: InventoryScope,
    itemId: string,
    params: StockLotsListParams,
  ): readonly [...Root, "list", StockLotsListParams] =>
    [...stockLotKeys.lists(scope, itemId), params] as const,
  detail: (
    scope: InventoryScope,
    itemId: string,
    lotId: string,
  ): readonly [...Root, "detail", string] =>
    [...stockLotKeys.root(scope, itemId), "detail", lotId] as const,
  update: (
    scope: InventoryScope,
    itemId: string,
    lotId: string,
  ): readonly [...Root, "update", string] =>
    [...stockLotKeys.root(scope, itemId), "update", lotId] as const,
  create: (
    scope: InventoryScope,
    itemId: string,
  ): readonly [...Root, "create"] =>
    [...stockLotKeys.root(scope, itemId), "create"] as const,
};
