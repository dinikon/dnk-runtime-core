import type { InventoryScope } from "./inventory-scope.types";
import type { WriteOffSourceParams } from "./write-off-posting.types";
export const writeOffPostingKeys = {
  root: (s: InventoryScope) =>
    ["inventory", ...s, "write-off-posting"] as const,
  context: (s: InventoryScope, id: string) =>
    [...writeOffPostingKeys.root(s), "context", id] as const,
  sources: (s: InventoryScope, id: string, p: WriteOffSourceParams) =>
    [...writeOffPostingKeys.root(s), "sources", id, { ...p }] as const,
  history: (s: InventoryScope, id: string, offset: number) =>
    [...writeOffPostingKeys.root(s), "history", id, offset] as const,
};
