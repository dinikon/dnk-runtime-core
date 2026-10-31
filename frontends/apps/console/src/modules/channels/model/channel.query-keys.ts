export type ChannelScope = readonly [string | null, string | null, string];
import type { ChannelFilters } from "./channel.types";
export const channelKeys = {
  root: (scope: ChannelScope) => ["channels", ...scope] as const,
  platforms: (scope: ChannelScope) =>
    [...channelKeys.root(scope), "platforms"] as const,
  list: (scope: ChannelScope, filters: ChannelFilters) =>
    [...channelKeys.root(scope), "list", filters] as const,
  detail: (scope: ChannelScope, id: string) =>
    [...channelKeys.root(scope), "detail", id] as const,
};
