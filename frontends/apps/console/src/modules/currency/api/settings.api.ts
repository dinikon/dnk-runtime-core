import { httpClient } from "@/app/providers/http";
import type {
  CurrencyInfo,
  CurrencySettings,
  CurrencyPolicy,
  PolicyInput,
  InitializeInput,
  RateSource,
} from "../model/types";
const base = "/console/currency";
export const currencySettingsApi = {
  directory: async () =>
    (await httpClient.get<CurrencyInfo[]>(`${base}/directory`)).data,
  settings: async () =>
    (await httpClient.get<CurrencySettings>(`${base}/settings`)).data,
  sources: async () =>
    (await httpClient.get<RateSource[]>(`${base}/sources`)).data,
  initialize: async (input: InitializeInput) =>
    (await httpClient.post(`${base}/initialize`, input)).data,
  configure: async (input: PolicyInput & { expected_version: number }) =>
    (await httpClient.put<CurrencyPolicy>(`${base}/policy`, input)).data,
  enable: async (code: string, enabled: boolean) =>
    (await httpClient.put(`${base}/enabled/${code}`, { enabled })).data,
};
