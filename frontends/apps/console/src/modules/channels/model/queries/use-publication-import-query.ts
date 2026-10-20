import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { publicationImportApi } from "../../api/publication-import.api";
import type { PublicationImport } from "../publication-import.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
import { channelsKeys } from "../channels.query-keys";
export function usePublicationImportQuery(
  ctx: ChannelsContext,
  id: MaybeRefOrGetter<string>,
  enabled: MaybeRefOrGetter<boolean>,
): UseQueryReturnType<PublicationImport, ChannelsApiError> {
  return useQuery<PublicationImport, ChannelsApiError>({
    queryKey: computed(() =>
      channelsKeys.publicationImport(ctx.scope.value, toValue(id)),
    ),
    queryFn: ({ signal }) => publicationImportApi.get(toValue(id), signal),
    enabled: computed(
      () => ctx.enabled.value && toValue(enabled) && !!toValue(id),
    ),
    refetchInterval: (query) =>
      query.state.error
        ? false
        : ["queued", "reading", "images"].includes(
              query.state.data?.status ?? "",
            )
          ? 900
          : false,
    refetchOnWindowFocus: false,
    retry: false,
  });
}
