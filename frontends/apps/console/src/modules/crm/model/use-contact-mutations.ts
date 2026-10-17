import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { getApiErrorMessage } from "@/app/providers/http";
import { crmContactsApi } from "../api/crm.api";
import { crmKeys } from "./crm.query-keys";
import type { ContactInput } from "./crm.types";

export function useCreateContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ContactInput) => crmContactsApi.create(input),
    onSuccess: async () => {
      toast.success("Контакт создан");
      await queryClient.invalidateQueries({ queryKey: crmKeys.all });
    },
    onError: (cause) =>
      toast.error(getApiErrorMessage(cause, "Не удалось создать контакт.")),
  });
}

export function useDeleteContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => crmContactsApi.delete(id),
    onSuccess: async () => {
      toast.success("Контакт удалён");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: crmKeys.list("contacts") }),
        queryClient.invalidateQueries({ queryKey: ["crm", "companies"] }),
      ]);
    },
    onError: (cause) =>
      toast.error(getApiErrorMessage(cause, "Не удалось удалить контакт.")),
  });
}
