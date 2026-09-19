import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { priceListsApi } from "../api/price-lists.api";
import { priceListKeys } from "./query-keys";

export type PriceListAction = "sync" | "pause" | "resume";

export function usePriceListAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: PriceListAction }) =>
      priceListsApi.action(id, action),
    onSuccess: async (_data, variables) => {
      toast.success("Действие поставлено в очередь");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: priceListKeys.list() }),
        queryClient.invalidateQueries({ queryKey: priceListKeys.detail(variables.id) }),
      ]);
    },
  });
}
