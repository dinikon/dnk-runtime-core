import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { stockApi } from "../api/stock.api";
import { stockKeys } from "./stock.query-keys";
import { stockActive, type BindingStock } from "./stock.types";
import { useChannelScope } from "./use-channel-scope";
export function useBindingStock(
  channel: MaybeRefOrGetter<string>,
  group: MaybeRefOrGetter<string>,
): UseQueryReturnType<BindingStock, Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() =>
      stockKeys.group(scope.value, toValue(channel), toValue(group)),
    ),
    queryFn: ({ signal }) =>
      stockApi.get(toValue(channel), toValue(group), signal),
    enabled: computed(
      () =>
        !!scope.value[0] &&
        !!scope.value[1] &&
        !!toValue(channel) &&
        !!toValue(group),
    ),
    retry: false,
    refetchInterval: (query) => (stockActive(query.state.data) ? 1500 : false),
  });
}
