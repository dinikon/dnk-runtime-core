import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { type UseQueryReturnType, useQuery } from "@tanstack/vue-query";
import type { PublicationsPage, PublicationsFilters } from "../channels.types";
import type { ChannelsApiError } from "../../api/channels.error";
import { channelsApi } from "../../api/channels.api";
import { channelsKeys } from "../channels.query-keys";
import type { ChannelsContext } from "../use-channels-context";
export function usePublicationsQuery(
  ctx: ChannelsContext,
  id: MaybeRefOrGetter<string>,
  filters: MaybeRefOrGetter<PublicationsFilters>,
  poll: MaybeRefOrGetter<boolean>,
): UseQueryReturnType<PublicationsPage, ChannelsApiError> {
  return useQuery<PublicationsPage, ChannelsApiError>({
    queryKey: computed(() =>
      channelsKeys.publications(ctx.scope.value, toValue(id), toValue(filters)),
    ),
    queryFn: ({ signal }) =>
      channelsApi.publications(toValue(id), toValue(filters), signal),
    enabled: computed(() => ctx.enabled.value && !!toValue(id)),
    retry: false,
    refetchIntervalInBackground: false,
    placeholderData: (previous, query) =>
      query?.queryKey[1] === ctx.scope.value &&
      query?.queryKey[3] === toValue(id)
        ? previous
        : undefined,
    refetchInterval: computed(() => (toValue(poll) ? 3000 : false)),
  });
}
