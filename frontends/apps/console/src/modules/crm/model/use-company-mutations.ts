import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { getApiErrorMessage } from "@/app/providers/http";
import { crmCompaniesApi } from "../api/crm.api";
import { crmKeys } from "./crm.query-keys";
import type { CompanyInput } from "./crm.types";

export function useCreateCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CompanyInput) => crmCompaniesApi.create(input),
    onSuccess: async () => {
      toast.success("Компания создана");
      await queryClient.invalidateQueries({ queryKey: crmKeys.all });
    },
    onError: (cause) =>
      toast.error(getApiErrorMessage(cause, "Не удалось создать компанию.")),
  });
}

export function useDeleteCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => crmCompaniesApi.delete(id),
    onSuccess: async () => {
      toast.success("Компания удалена");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: crmKeys.list("companies") }),
        queryClient.invalidateQueries({ queryKey: ["crm", "contacts"] }),
      ]);
    },
    onError: (cause) =>
      toast.error(getApiErrorMessage(cause, "Не удалось удалить компанию.")),
  });
}
