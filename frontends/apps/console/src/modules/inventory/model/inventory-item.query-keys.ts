import type { InventoryItemsListParams } from "./inventory-item.types.ts";
import type { InventoryScope } from "./inventory-scope.types.ts";

type InventoryRootKey = readonly ["inventory", ...InventoryScope];
type InventoryListKey = readonly [
  ...InventoryRootKey,
  "items",
  "list",
  InventoryItemsListParams,
];

export const inventoryItemKeys = {
  root: (scope: InventoryScope): InventoryRootKey => ["inventory", ...scope],
  create: (scope: InventoryScope): readonly [...InventoryRootKey, "create"] => [
    ...inventoryItemKeys.root(scope),
    "create",
  ],
  detail: (
    scope: InventoryScope,
    id: string,
  ): readonly [...InventoryRootKey, "items", "detail", string] => [
    ...inventoryItemKeys.root(scope),
    "items",
    "detail",
    id,
  ],
  lists: (
    scope: InventoryScope,
  ): readonly [...InventoryRootKey, "items", "list"] => [
    ...inventoryItemKeys.root(scope),
    "items",
    "list",
  ],
  uoms: (scope: InventoryScope): readonly [...InventoryRootKey, "uoms"] => [
    ...inventoryItemKeys.root(scope),
    "uoms",
  ],
  update: (
    scope: InventoryScope,
    id: string,
  ): readonly [...InventoryRootKey, "items", "update", string] => [
    ...inventoryItemKeys.root(scope),
    "items",
    "update",
    id,
  ],
  delete: (
    scope: InventoryScope,
    id: string,
  ): readonly [...InventoryRootKey, "items", "delete", string] => [
    ...inventoryItemKeys.root(scope),
    "items",
    "delete",
    id,
  ],
  settings: (
    scope: InventoryScope,
  ): readonly [...InventoryRootKey, "settings"] => [
    ...inventoryItemKeys.root(scope),
    "settings",
  ],
  list: (
    scope: InventoryScope,
    params: InventoryItemsListParams,
  ): InventoryListKey => [
    ...inventoryItemKeys.root(scope),
    "items",
    "list",
    { ...params },
  ],
};
