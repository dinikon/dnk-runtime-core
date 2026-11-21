import type { InventoryScope } from "./inventory-scope.types";
import type {
  InternalMoveSourceParams,
  InternalMoveDestinationParams,
} from "./internal-move-posting.types";
export const internalMovePostingKeys = {
  root: (s: InventoryScope) =>
    ["inventory", ...s, "internal-move-posting"] as const,
  context: (s: InventoryScope, id: string) =>
    [...internalMovePostingKeys.root(s), "context", id] as const,
  sources: (s: InventoryScope, id: string, p: InternalMoveSourceParams) =>
    [...internalMovePostingKeys.root(s), "sources", id, { ...p }] as const,
  destinations: (
    s: InventoryScope,
    id: string,
    p: InternalMoveDestinationParams,
  ) =>
    [...internalMovePostingKeys.root(s), "destinations", id, { ...p }] as const,
  history: (s: InventoryScope, id: string, offset: number) =>
    [...internalMovePostingKeys.root(s), "history", id, offset] as const,
};
