import type { InventoryScope } from "./inventory-scope.types.ts";
import type { PackagingTypesListParams } from "./packaging-type.types.ts";
type Root = readonly ["inventory", ...InventoryScope, "packaging-types"];
export const packagingTypeKeys = {
  root: (scope: InventoryScope): Root => [
    "inventory",
    ...scope,
    "packaging-types",
  ],
  lists: (scope: InventoryScope): readonly [...Root, "list"] => [
    ...packagingTypeKeys.root(scope),
    "list",
  ],
  list: (
    scope: InventoryScope,
    params: PackagingTypesListParams,
  ): readonly [...Root, "list", PackagingTypesListParams] => [
    ...packagingTypeKeys.lists(scope),
    { ...params },
  ],
  detail: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "detail", string] => [
    ...packagingTypeKeys.root(scope),
    "detail",
    id,
  ],
  candidates: (scope: InventoryScope, search: string): readonly [...Root, "candidates", PackagingTypesListParams] => [
    ...packagingTypeKeys.root(scope), "candidates", {search,isActive:true,offset:0,limit:20},
  ],
  create: (scope: InventoryScope): readonly [...Root, "create"] => [
    ...packagingTypeKeys.root(scope),
    "create",
  ],
  update: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "update", string] => [
    ...packagingTypeKeys.root(scope),
    "update",
    id,
  ],
};
