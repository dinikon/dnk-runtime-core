import { httpClient } from "@/app/providers/http";
import type { RateRecord } from "../model/types";
const base = "/console/currency";
export const currencyRatesApi = {
  rates: async (provider: string, offset: number) =>
    (
      await httpClient.get<RateRecord[]>(`${base}/rates`, {
        params: { provider, offset, limit: 50 },
      })
    ).data,
  manual: async (input: {
    source_currency: string;
    target_currency: string;
    rate: string;
    effective_date: string;
  }) => (await httpClient.post(`${base}/rates/manual`, input)).data,
};
