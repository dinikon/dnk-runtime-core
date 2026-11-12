import type { InventoryScope } from "./inventory-scope.types.ts";
import type { WarehousesListParams } from "./warehouse.types.ts";
type Root = readonly ["inventory", ...InventoryScope, "warehouses"];
export const warehouseKeys = {
  root: (scope: InventoryScope): Root => ["inventory", ...scope, "warehouses"],
  lists: (scope: InventoryScope): readonly [...Root, "list"] => [
    ...warehouseKeys.root(scope),
    "list",
  ],
  list: (
    scope: InventoryScope,
    params: WarehousesListParams,
  ): readonly [...Root, "list", WarehousesListParams] => [
    ...warehouseKeys.lists(scope),
    { ...params },
  ],
  detail: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "detail", string] => [
    ...warehouseKeys.root(scope),
    "detail",
    id,
  ],
  create: (scope: InventoryScope): readonly [...Root, "create"] => [
    ...warehouseKeys.root(scope),
    "create",
  ],
  update: (scope: InventoryScope): readonly [...Root, "update"] => [
    ...warehouseKeys.root(scope),
    "update",
  ],
};
