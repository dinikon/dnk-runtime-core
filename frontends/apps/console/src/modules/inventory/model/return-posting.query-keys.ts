import type { InventoryScope } from "./inventory-scope.types";
import type {
  ReturnSourceParams,
  ReturnDestinationParams,
} from "./return-posting.types";
type Root = readonly ["inventory", ...InventoryScope, "return-posting"];
export const returnPostingKeys = {
  root: (scope: InventoryScope): Root =>
    ["inventory", ...scope, "return-posting"] as const,
  result: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "result", string] =>
    [...returnPostingKeys.root(scope), "result", id] as const,
  destinations: (
    scope: InventoryScope,
    id: string,
    params: ReturnDestinationParams,
  ): readonly [...Root, "destinations", string, ReturnDestinationParams] =>
    [
      ...returnPostingKeys.root(scope),
      "destinations",
      id,
      { ...params },
    ] as const,
  preview: (
    scope: InventoryScope,
    id: string,
    signature: string,
  ): readonly [...Root, "preview", string, string] =>
    [...returnPostingKeys.root(scope), "preview", id, signature] as const,
  context: (
    scope: InventoryScope,
    id: string,
  ): readonly [...Root, "context", string] =>
    [...returnPostingKeys.root(scope), "context", id] as const,
  sources: (
    scope: InventoryScope,
    id: string,
    params: ReturnSourceParams,
  ): readonly [...Root, "sources", string, ReturnSourceParams] =>
    [...returnPostingKeys.root(scope), "sources", id, { ...params }] as const,
  history: (
    scope: InventoryScope,
    id: string,
    offset: number,
  ): readonly [...Root, "history", string, number] =>
    [...returnPostingKeys.root(scope), "history", id, offset] as const,
};
