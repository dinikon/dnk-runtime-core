import { channelKeys, type ChannelScope } from "./channel.query-keys";
export const stockKeys = {
  group: (scope: ChannelScope, channel: string, group: string) =>
    [...channelKeys.root(scope), "stock", channel, group] as const,
};
