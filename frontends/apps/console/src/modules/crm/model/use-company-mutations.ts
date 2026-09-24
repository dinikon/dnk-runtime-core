import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { getApiErrorMessage } from "@/app/providers/http";
import { crmCompaniesApi } from "../api/crm.api";
import { companyKeys } from "./crm.query-keys";
import type { CompanyInput } from "./crm.types";

export function useCreateCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CompanyInput) => crmCompaniesApi.create(input),
    onSuccess: async () => {
      toast.success("Компания создана");
      await queryClient.invalidateQueries({ queryKey: companyKeys.all });
    },
    onError: (cause) =>
      toast.error(getApiErrorMessage(cause, "Не удалось создать компанию.")),
  });
}

export function useUpdateCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: CompanyInput }) =>
      crmCompaniesApi.update(id, input),
    onSuccess: async () => {
      toast.success("Компания обновлена");
      await queryClient.invalidateQueries({ queryKey: companyKeys.all });
    },
    onError: (cause) =>
      toast.error(getApiErrorMessage(cause, "Не удалось обновить компанию.")),
  });
}

export function useDeleteCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => crmCompaniesApi.delete(id),
    onSuccess: async () => {
      toast.success("Компания удалена");
      await queryClient.invalidateQueries({ queryKey: companyKeys.all });
    },
    onError: (cause) =>
      toast.error(getApiErrorMessage(cause, "Не удалось удалить компанию.")),
  });
}
