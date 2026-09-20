import { httpClient } from "@/app/providers/http";
import type {
  CurrencyInfo,
  CurrencySettings,
  RateRecord,
  PolicyInput,
  InitializeInput,
} from "../model/types";

const base = "/console/currency";
export const currencyApi = {
  directory: async () =>
    (await httpClient.get<CurrencyInfo[]>(`${base}/directory`)).data,
  settings: async () =>
    (await httpClient.get<CurrencySettings>(`${base}/settings`)).data,
  initialize: async (input: InitializeInput) =>
    (await httpClient.post(`${base}/initialize`, input)).data,
  configure: async (input: PolicyInput & { expected_version: number }) =>
    (await httpClient.put(`${base}/policy`, input)).data,
  enable: async (code: string, enabled: boolean) =>
    (await httpClient.put(`${base}/enabled/${code}`, { enabled })).data,
  schedule: async (input: {
    currency: string;
    effective_from: string;
    reason: string;
  }) => (await httpClient.post(`${base}/periods`, input)).data,
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
