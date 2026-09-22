import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { getApiErrorMessage } from "@/app/providers/http";
import { crmContactsApi } from "../api/crm.api";
import { contactKeys } from "./crm.query-keys";
import type { ContactInput } from "./crm.types";

export function useCreateContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ContactInput) => crmContactsApi.create(input),
    onSuccess: async () => {
      toast.success("Контакт создан");
      await queryClient.invalidateQueries({ queryKey: contactKeys.all });
    },
    onError: (cause) =>
      toast.error(getApiErrorMessage(cause, "Не удалось создать контакт.")),
  });
}

export function useUpdateContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: ContactInput }) =>
      crmContactsApi.update(id, input),
    onSuccess: async () => {
      toast.success("Контакт обновлён");
      await queryClient.invalidateQueries({ queryKey: contactKeys.all });
    },
    onError: (cause) =>
      toast.error(getApiErrorMessage(cause, "Не удалось обновить контакт.")),
  });
}

export function useDeleteContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => crmContactsApi.delete(id),
    onSuccess: async () => {
      toast.success("Контакт удалён");
      await queryClient.invalidateQueries({ queryKey: contactKeys.all });
    },
    onError: (cause) =>
      toast.error(getApiErrorMessage(cause, "Не удалось удалить контакт.")),
  });
}
