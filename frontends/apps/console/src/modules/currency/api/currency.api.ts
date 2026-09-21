import { currencySettingsApi } from "./settings.api";
import { currencyRatesApi } from "./rates.api";
import { currencyPeriodsApi } from "./periods.api";
export const currencyApi = {
  ...currencySettingsApi,
  ...currencyRatesApi,
  ...currencyPeriodsApi,
};
