import { channelKeys, type ChannelScope } from "./channel.query-keys";

export const contentDeliveryKeys = {
  detail: (scope: ChannelScope, channelId: string, groupId: string) =>
    [
      ...channelKeys.root(scope),
      "content-deliveries",
      channelId,
      groupId,
    ] as const,
  mutation: (scope: ChannelScope, action: string) =>
    [...channelKeys.root(scope), "content-deliveries", action] as const,
};
