import type { InventoryScope } from "./inventory-scope.types";
import type { IssueSourceParams } from "./issue-posting.types";
export const issuePostingKeys = {
  root: (s: InventoryScope) => ["inventory", ...s, "issue-posting"] as const,
  context: (s: InventoryScope, id: string) =>
    [...issuePostingKeys.root(s), "context", id] as const,
  sources: (s: InventoryScope, id: string, p: IssueSourceParams) =>
    [...issuePostingKeys.root(s), "sources", id, { ...p }] as const,
  history: (s: InventoryScope, id: string, offset: number) =>
    [...issuePostingKeys.root(s), "history", id, offset] as const,
};
