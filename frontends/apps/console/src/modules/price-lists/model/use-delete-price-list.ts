import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { getApiErrorMessage } from "@/app/providers/http";
import { priceListsApi } from "../api/price-lists.api";
import { priceListKeys } from "./query-keys";

export function useDeletePriceList() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, confirmationTitle }: { id: string; confirmationTitle: string }) =>
      priceListsApi.delete(id, confirmationTitle),
    onSuccess: async () => {
      toast.success("Прайс-лист удалён окончательно");
      await queryClient.invalidateQueries({ queryKey: priceListKeys.all });
    },
    onError: (cause) => toast.error(getApiErrorMessage(cause, "Не удалось удалить прайс-лист.")),
  });
}
