import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { feedSchemaApi } from "../api/feed-schema.api";
import { feedSchemaKeys } from "./feed-schema.query-keys";
import { useFeedScope } from "./use-feed-scope";
import type { FeedSchema, SchemaMetadata } from "./feed-schema.types";
export function useFeedSchema(
  id: Ref<string>,
): UseQueryReturnType<FeedSchema, Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() => feedSchemaKeys.detail(scope.value, id.value)),
    queryFn: ({ signal }) => feedSchemaApi.get(id.value, signal),
    enabled: computed(() => !!scope.value[0] && !!scope.value[1] && !!id.value),
    retry: false,
  });
}
export function useSchemaMetadata(): UseQueryReturnType<SchemaMetadata, Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() => feedSchemaKeys.metadata(scope.value)),
    queryFn: ({ signal }) => feedSchemaApi.metadata(signal),
    enabled: computed(() => !!scope.value[0] && !!scope.value[1]),
    staleTime: 300000,
    retry: false,
  });
}
