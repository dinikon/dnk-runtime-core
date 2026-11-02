import { channelApi } from "../api/channel.api";
import type { ChannelSave, ChannelSaved } from "./channel.types";
import { useChannelAction, type ChannelAction } from "./use-channel-action";

interface UpdateChannelInput {
  id: string;
  revision: number;
  value: ChannelSave;
}

export function useUpdateChannel(): ChannelAction<
  UpdateChannelInput,
  ChannelSaved
> {
  return useChannelAction((input: UpdateChannelInput, signal) =>
    channelApi.update(input.id, input.value, input.revision, signal),
  );
}
