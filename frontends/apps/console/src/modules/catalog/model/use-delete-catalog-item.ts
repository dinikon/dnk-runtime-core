import { toValue, watch, type MaybeRefOrGetter } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { catalogApi } from "../api/catalog.api";
import { catalogListKeys } from "./catalog-list.query-keys";

export function useDeleteCatalogItem(
  tenant: MaybeRefOrGetter<string>,
  session: MaybeRefOrGetter<string>,
): UseMutationReturnType<void, Error, string, readonly string[]> {
  const cache = useQueryClient();
  const mutation = useMutation({
    mutationFn: (id: string) => catalogApi.deleteItem(id),
    retry: false,
    onMutate: () => catalogListKeys.all(toValue(tenant), toValue(session)),
    onSuccess: async (_data, _id, captured) => {
      const current = catalogListKeys.all(toValue(tenant), toValue(session));
      if (
        captured &&
        captured.every((value, index) => value === current[index])
      )
        await cache.invalidateQueries({
          queryKey: ["catalog", toValue(tenant)],
        });
    },
  });
  watch(
    () => [toValue(tenant), toValue(session)],
    () => mutation.reset(),
  );
  return mutation;
}
