import { computed, toValue, type MaybeRefOrGetter } from "vue";
import {
  useQuery,
  type UseQueryReturnType,
  keepPreviousData,
} from "@tanstack/vue-query";
import { catalogLinksApi } from "../../api/catalog-links.api";
import type {
  CatalogCandidatesPage,
  CatalogCandidatesInput,
} from "../catalog-links.types";
import type { ChannelsApiError } from "../../api/channels.error";
import { channelsKeys } from "../channels.query-keys";
import type { ChannelsContext } from "../use-channels-context";
export function useCatalogCandidatesQuery(
  ctx: ChannelsContext,
  input: MaybeRefOrGetter<CatalogCandidatesInput>,
  enabled: MaybeRefOrGetter<boolean>,
): UseQueryReturnType<CatalogCandidatesPage, ChannelsApiError> {
  return useQuery<CatalogCandidatesPage, ChannelsApiError>({
    queryKey: computed(() =>
      channelsKeys.candidates(ctx.scope.value, toValue(input)),
    ),
    queryFn: ({ signal }) => catalogLinksApi.candidates(toValue(input), signal),
    enabled: computed(
      () => ctx.enabled.value && toValue(enabled) && !!toValue(input).locale,
    ),
    retry: false,
    placeholderData: keepPreviousData,
  });
}
