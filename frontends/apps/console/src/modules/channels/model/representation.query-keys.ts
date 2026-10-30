import { bindingKeys } from "./bindings/binding.query-keys";
import type { ChannelScope } from "./channel.query-keys";

export const representationKeys = {
  mutation: (scope: ChannelScope, action: "save" | "enable" | "disable") =>
    [...bindingKeys.root(scope), "representation", action] as const,
  root: (scope: ChannelScope, channelId: string, groupId: string) =>
    [...bindingKeys.root(scope), "representation", channelId, groupId] as const,
  detail: (scope: ChannelScope, channelId: string, groupId: string) =>
    [...representationKeys.root(scope, channelId, groupId), "detail"] as const,
  preview: (scope: ChannelScope, channelId: string, groupId: string) =>
    [...representationKeys.root(scope, channelId, groupId), "preview"] as const,
};
