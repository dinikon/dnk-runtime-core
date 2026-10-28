import { channelApi } from "../api/channel.api";
import { useChannelAction } from "./use-channel-action";
import type { ChannelAction } from "./use-channel-action";
import type { ChannelSaved } from "./channel.types";
export function useVerifyChannel(): ChannelAction<string, ChannelSaved> {
  return useChannelAction((id: string, signal) =>
    channelApi.verify(id, signal),
  );
}
