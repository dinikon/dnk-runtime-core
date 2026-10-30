import type { ChannelScope } from "./channel.query-keys";
import { channelKeys } from "./channel.query-keys";
export const contentFeedKeys = {
  list: (scope: ChannelScope, channelId: string) =>
    [...channelKeys.root(scope), "content-feeds", channelId] as const,
  operation: (scope: ChannelScope, channelId: string, feedId: string) =>
    [...contentFeedKeys.list(scope, channelId), feedId, "import"] as const,
  mutation: (scope: ChannelScope, action: string) =>
    [...channelKeys.root(scope), "content-feed-mutation", action] as const,
};
