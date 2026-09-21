import { httpClient } from "@/app/providers/http";
export const currencyPeriodsApi = {
  schedule: async (input: {
    currency: string;
    effective_from: string;
    reason: string;
  }) => (await httpClient.post("/console/currency/periods", input)).data,
};
