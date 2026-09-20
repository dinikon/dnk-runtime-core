import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { getApiErrorMessage } from "@/app/providers/http";
import { priceListsApi } from "../api/price-lists.api";
import { priceListKeys } from "./query-keys";

export type PriceListAction = "sync" | "pause" | "resume" | "archive" | "restore";

export function usePriceListAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: PriceListAction }) =>
      priceListsApi.action(id, action),
    onSuccess: async (_data, variables) => {
      toast.success(variables.action === "archive" ? "Прайс-лист архивирован" : variables.action === "restore" ? "Прайс-лист восстановлен" : "Действие выполнено");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: priceListKeys.all }),
        queryClient.invalidateQueries({ queryKey: priceListKeys.detail(variables.id) }),
      ]);
    },
    onError: (cause) => toast.error(getApiErrorMessage(cause, "Не удалось выполнить действие.")),
  });
}
