import type { InventoryScope } from "./inventory-scope.types";
import type { IssuesParams } from "./issue.types";
type Root = readonly ["inventory", ...InventoryScope, "stock-documents/issues"];
export const issueKeys = {
  root: (scope: InventoryScope): Root =>
    ["inventory", ...scope, "stock-documents/issues"] as const,
  lists: (scope: InventoryScope): readonly [...Root, "list"] =>
    [...issueKeys.root(scope), "list"] as const,
  list: (
    scope: InventoryScope,
    p: IssuesParams,
  ): readonly [...Root, "list", IssuesParams] =>
    [...issueKeys.lists(scope), { ...p }] as const,
  detail: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "detail", string] =>
    [...issueKeys.root(scope), "detail", id] as const,
  update: (scope: InventoryScope): readonly [...Root, "update"] =>
    [...issueKeys.root(scope), "update"] as const,
  confirm: (scope: InventoryScope): readonly [...Root, "confirm"] =>
    [...issueKeys.root(scope), "confirm"] as const,
  cancel: (scope: InventoryScope): readonly [...Root, "cancel"] =>
    [...issueKeys.root(scope), "cancel"] as const,
  create: (scope: InventoryScope): readonly [...Root, "create"] =>
    [...issueKeys.root(scope), "create"] as const,
};
