import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { catalogLinksApi } from "../../api/catalog-links.api";
import type { PublicationSnapshot } from "../catalog-links.types";
import type { ChannelsApiError } from "../../api/channels.error";
import { channelsKeys } from "../channels.query-keys";
import type { ChannelsContext } from "../use-channels-context";
export function usePublicationSnapshotQuery(
  ctx: ChannelsContext,
  id: MaybeRefOrGetter<string>,
): UseQueryReturnType<PublicationSnapshot, ChannelsApiError> {
  return useQuery<PublicationSnapshot, ChannelsApiError>({
    queryKey: computed(() =>
      channelsKeys.publicationSnapshot(ctx.scope.value, toValue(id)),
    ),
    queryFn: ({ signal }) => catalogLinksApi.source(toValue(id), signal),
    enabled: computed(() => ctx.enabled.value && !!toValue(id)),
    retry: false,
    refetchOnWindowFocus: false,
  });
}
