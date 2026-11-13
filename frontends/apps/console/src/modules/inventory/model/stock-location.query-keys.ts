import type { InventoryScope } from "./inventory-scope.types.ts";
import type { StockLocationsListParams } from "./stock-location.types.ts";
type Root = readonly [
  "inventory",
  ...InventoryScope,
  "stock-locations",
  string,
];
export const stockLocationKeys = {
  root: (scope: InventoryScope, warehouseId: string): Root => [
    "inventory",
    ...scope,
    "stock-locations",
    warehouseId,
  ],
  lists: (
    scope: InventoryScope,
    warehouseId: string,
  ): readonly [...Root, "list"] => [
    ...stockLocationKeys.root(scope, warehouseId),
    "list",
  ],
  list: (
    scope: InventoryScope,
    warehouseId: string,
    params: StockLocationsListParams,
  ): readonly [...Root, "list", StockLocationsListParams] => [
    ...stockLocationKeys.lists(scope, warehouseId),
    { ...params },
  ],
  detail: (
    scope: InventoryScope,
    warehouseId: string,
    id: string,
  ): readonly [...Root, "detail", string] => [
    ...stockLocationKeys.root(scope, warehouseId),
    "detail",
    id,
  ],
  parentSearches: (
    scope: InventoryScope,
    warehouseId: string,
  ): readonly [...Root, "parents"] => [
    ...stockLocationKeys.root(scope, warehouseId),
    "parents",
  ],
  parents: (
    scope: InventoryScope,
    warehouseId: string,
    search: string,
  ): readonly [
    ...Root,
    "parents",
    Omit<StockLocationsListParams, "offset">,
  ] => [
    ...stockLocationKeys.parentSearches(scope, warehouseId),
    {
      search,
      limit: 50,
      isActive: null,
      locationType: null,
      parentLocationId: null,
    },
  ],
  create: (
    scope: InventoryScope,
    warehouseId: string,
  ): readonly [...Root, "create"] => [
    ...stockLocationKeys.root(scope, warehouseId),
    "create",
  ],
  defaultStorageCandidates: (
    scope: InventoryScope,
    warehouseId: string,
    search: string,
  ): readonly [
    ...Root,
    "default-storage-candidates",
    Omit<StockLocationsListParams, "offset">,
  ] => [
    ...stockLocationKeys.root(scope, warehouseId),
    "default-storage-candidates",
    {
      search,
      limit: 50,
      isActive: true,
      locationType: "STORAGE",
      parentLocationId: null,
    },
  ],
  update: (
    scope: InventoryScope,
    warehouseId: string,
  ): readonly [...Root, "update"] => [
    ...stockLocationKeys.root(scope, warehouseId),
    "update",
  ],
};
