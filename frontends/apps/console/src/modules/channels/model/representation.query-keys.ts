import { bindingKeys } from "./bindings/binding.query-keys";
import type { ChannelScope } from "./channel.query-keys";

export const representationKeys = {
  preview: (scope: ChannelScope, channelId: string, groupId: string) =>
    [...bindingKeys.root(scope), "representation", channelId, groupId] as const,
};
