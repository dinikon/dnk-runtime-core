import type { InventoryScope } from "./inventory-scope.types";
import type { StatusChangeSourceParams } from "./status-change-posting.types";
export const statusChangePostingKeys = {
  root: (s: InventoryScope) =>
    ["inventory", ...s, "status-change-posting"] as const,
  result: (s: InventoryScope, id: string) =>
    [...statusChangePostingKeys.root(s), "result", id] as const,
  transitions: (s: InventoryScope) =>
    [...statusChangePostingKeys.root(s), "transitions"] as const,
  preview: (s: InventoryScope, id: string, signature: string) =>
    [...statusChangePostingKeys.root(s), "preview", id, signature] as const,
  context: (s: InventoryScope, id: string) =>
    [...statusChangePostingKeys.root(s), "context", id] as const,
  sources: (s: InventoryScope, id: string, p: StatusChangeSourceParams) =>
    [...statusChangePostingKeys.root(s), "sources", id, { ...p }] as const,
  history: (s: InventoryScope, id: string, offset: number) =>
    [...statusChangePostingKeys.root(s), "history", id, offset] as const,
};
