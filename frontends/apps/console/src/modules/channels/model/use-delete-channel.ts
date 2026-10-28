import { channelApi } from "../api/channel.api";
import { useChannelAction } from "./use-channel-action";
import type { ChannelAction } from "./use-channel-action";
import { useQueryClient } from "@tanstack/vue-query";
import { useChannelScope } from "./use-channel-scope";
import { channelKeys } from "./channel.query-keys";
export function useDeleteChannel(): ChannelAction<
  { id: string; revision: number },
  void
> {
  const scope = useChannelScope(),
    cache = useQueryClient();
  return useChannelAction(
    async (input: { id: string; revision: number }, signal) => {
      const key = channelKeys.detail(scope.value, input.id);
      await channelApi.delete(input.id, input.revision, signal);
      cache.removeQueries({ queryKey: key, exact: true });
    },
  );
}
