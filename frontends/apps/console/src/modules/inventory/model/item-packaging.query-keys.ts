import type { InventoryScope } from "./inventory-scope.types.ts";
import type { ItemPackagingsListParams } from "./item-packaging.types.ts";
type Root = readonly [
  "inventory",
  ...InventoryScope,
  "item-packagings",
  string,
];
export const itemPackagingKeys = {
  root: (scope: InventoryScope, itemId: string): Root => [
    "inventory",
    ...scope,
    "item-packagings",
    itemId,
  ],
  lists: (
    scope: InventoryScope,
    itemId: string,
  ): readonly [...Root, "list"] => [
    ...itemPackagingKeys.root(scope, itemId),
    "list",
  ],
  list: (
    scope: InventoryScope,
    itemId: string,
    params: ItemPackagingsListParams,
  ): readonly [...Root, "list", ItemPackagingsListParams] => [
    ...itemPackagingKeys.lists(scope, itemId),
    { ...params },
  ],
  detail: (
    scope: InventoryScope,
    itemId: string,
    id: string,
  ): readonly [...Root, "detail", string] => [
    ...itemPackagingKeys.root(scope, itemId),
    "detail",
    id,
  ],
  create: (
    scope: InventoryScope,
    itemId: string,
  ): readonly [...Root, "create"] => [
    ...itemPackagingKeys.root(scope, itemId),
    "create",
  ],
  update: (
    scope: InventoryScope,
    itemId: string,
    id: string,
  ): readonly [...Root, "update", string] => [
    ...itemPackagingKeys.root(scope, itemId),
    "update",
    id,
  ],
};
