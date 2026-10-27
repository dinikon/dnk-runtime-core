import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { channelApi } from "../api/channel.api";
import { useChannelScope } from "./use-channel-scope";
import { channelKeys } from "./channel.query-keys";
import { shouldPoll } from "./channel.schema";
import type {
  Channel,
  ChannelPage,
  ChannelFilters,
  Platform,
} from "./channel.types";
export function useChannelPlatforms(): UseQueryReturnType<Platform[], Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() => channelKeys.platforms(scope.value)),
    queryFn: ({ signal }) => channelApi.platforms(signal),
    enabled: computed(() => !!scope.value[0] && !!scope.value[1]),
    staleTime: 300000,
  });
}
export function useChannels(
  filters: Ref<ChannelFilters>,
): UseQueryReturnType<ChannelPage, Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() => channelKeys.list(scope.value, filters.value)),
    queryFn: ({ signal }) => channelApi.list(filters.value, signal),
    enabled: computed(() => !!scope.value[0] && !!scope.value[1]),
    refetchInterval: (query) =>
      query.state.data?.items.some(shouldPoll) ? 2000 : false,
  });
}
export function useChannel(
  id: Ref<string>,
): UseQueryReturnType<Channel, Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() => channelKeys.detail(scope.value, id.value)),
    queryFn: ({ signal }) => channelApi.get(id.value, signal),
    enabled: computed(() => !!id.value && !!scope.value[0] && !!scope.value[1]),
    retry: false,
    refetchInterval: (query) =>
      query.state.data && shouldPoll(query.state.data) ? 2000 : false,
  });
}
