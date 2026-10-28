import { channelApi } from "../api/channel.api";
import type { ChannelSave, ChannelSaved } from "./channel.types";
import type { ChannelAction } from "./use-channel-action";
import { useChannelAction } from "./use-channel-action";
type SaveInput = { id?: string; revision?: number; value: ChannelSave };
export function useSaveChannel(): ChannelAction<SaveInput, ChannelSaved> {
  return useChannelAction(
    (input: { id?: string; revision?: number; value: ChannelSave }, signal) =>
      input.id
        ? channelApi.update(input.id, input.value, input.revision!, signal)
        : channelApi.create(input.value, signal),
  );
}
