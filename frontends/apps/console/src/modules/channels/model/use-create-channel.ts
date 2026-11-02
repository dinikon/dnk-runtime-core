import { channelApi } from "../api/channel.api";
import type { ChannelSave, ChannelSaved } from "./channel.types";
import { useChannelAction, type ChannelAction } from "./use-channel-action";

export function useCreateChannel(): ChannelAction<ChannelSave, ChannelSaved> {
  return useChannelAction((value: ChannelSave, signal) =>
    channelApi.create(value, signal),
  );
}
