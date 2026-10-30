import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { stockApi } from "../api/stock.api";
import { stockKeys } from "./stock.query-keys";
import { useChannelScope } from "./use-channel-scope";
import type { ChannelScope } from "./channel.query-keys";
import type { StockRequest } from "./stock.types";
export function useExportCatalogStock(): UseMutationReturnType<
  string[],
  Error,
  StockRequest,
  ChannelScope
> {
  const scope = useChannelScope(),
    cache = useQueryClient();
  return useMutation({
    mutationFn: stockApi.export,
    retry: false,
    onMutate: () => [...scope.value] as ChannelScope,
    onSuccess: (_result, input, previous) =>
      cache.invalidateQueries({
        queryKey: stockKeys.group(previous, input.channelId, input.groupId),
      }),
  });
}
