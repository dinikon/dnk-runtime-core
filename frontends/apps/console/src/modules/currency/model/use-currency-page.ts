import { useSetEnabledCurrencyMutation } from "./use-set-enabled-currency-mutation";
import { useScheduleFunctionalCurrencyMutation } from "./use-schedule-functional-currency-mutation";
import { useSetManualRateMutation } from "./use-set-manual-rate-mutation";
import { useConfigurePolicyMutation } from "./use-configure-policy-mutation";
import { useInitializeCurrencyMutation } from "./use-initialize-currency-mutation";
import { computed, reactive, ref, watch } from "vue";
import { isAxiosError } from "axios";
import { toast } from "vue-sonner";

import {
  useCurrencySources,
  useCurrencyDirectory,
  useCurrencySettings,
  useCurrencyRates,
  useRefreshCurrency,
} from "./queries";
import type { PolicyInput } from "./types";

export function useCurrencyPage() {
  const initializeMutation = useInitializeCurrencyMutation();
  const policyMutation = useConfigurePolicyMutation();
  const manualMutation = useSetManualRateMutation();
  const scheduleMutation = useScheduleFunctionalCurrencyMutation();
  const enabledMutation = useSetEnabledCurrencyMutation();
  const setManualRate = manualMutation.mutateAsync;
  const schedulePeriod = scheduleMutation.mutateAsync;
  const setEnabledCurrency = (code: string, enabled: boolean) =>
    enabledMutation.mutateAsync({ code, enabled });
  const settingsQuery = useCurrencySettings();
  const sourcesQuery = useCurrencySources();
  const sources = computed(() => sourcesQuery.data.value ?? []);
  const directoryQuery = useCurrencyDirectory();
  const refresh = useRefreshCurrency();
  const settings = computed(() => settingsQuery.data.value);
  const currencies = computed(() => directoryQuery.data.value ?? []);
  const allowed = computed(() =>
    currencies.value.filter((c) =>
      settings.value?.enabled_currencies.includes(c.code),
    ),
  );
  const can = (permission: string) =>
    settings.value?.permissions.includes(permission) ?? false;
  const pending = ref(false);
  const error = ref("");
  const conflict = ref(false);
  const statusLabels: Record<string, string> = {
    running: "Загрузка",
    succeeded: "Успешно",
    failed: "Ошибка",
  };
  const provider = ref("NBU");
  const offset = ref(0);
  watch(provider, () => {
    offset.value = 0;
  });
  const ratesQuery = useCurrencyRates(provider, offset);
  const policy = reactive<PolicyInput>({
    default_transaction_currency: "UAH",
    provider_code: "NBU",
    rate_date_policy: "previous_available",
    rounding_mode: "ROUND_HALF_UP",
    allow_cross_rate: true,
    bridge_currency: "UAH",
    business_timezone: "Europe/Kyiv",
    default_display_currency: null,
  });
  const expectedVersion = ref(0);
  const functional = ref("UAH");
  const initialFrom = ref("");
  const initialEnabled = ref(["UAH", "USD", "EUR"]);
  const search = ref("");
  const visibleCurrencies = computed(() =>
    currencies.value.filter((c) =>
      `${c.code} ${c.name}`.toLowerCase().includes(search.value.toLowerCase()),
    ),
  );
  const manual = reactive({
    source_currency: "USD",
    target_currency: "UAH",
    rate: "",
    effective_date: "",
  });
  const schedule = reactive({
    currency: "EUR",
    effective_from: "",
    reason: "",
  });
  // Populate once; background refresh must never overwrite an administrator's edits.
  watch(
    settings,
    (value) => {
      if (!value) return;
      initialFrom.value ||= value.business_date;
      manual.effective_date ||= value.business_date;
      if (value.policy && !expectedVersion.value) {
        const { version, ...rest } = value.policy;
        Object.assign(policy, rest);
        expectedVersion.value = version;
      }
    },
    { immediate: true },
  );

  function policyInput(): PolicyInput {
    return { ...policy };
  }
  async function action(operation: () => Promise<unknown>) {
    if (pending.value) return;
    error.value = "";
    conflict.value = false;
    pending.value = true;
    try {
      await operation();
      await refresh();
      toast.success("Изменения сохранены");
    } catch (cause) {
      conflict.value = isAxiosError(cause) && cause.response?.status === 409;
      const detail = isAxiosError(cause) ? cause.response?.data?.detail : null;
      error.value = conflict.value
        ? "Настройки изменились или операция конфликтует с текущими данными. Обновите данные перед повторным сохранением."
        : typeof detail === "string"
          ? detail
          : (detail?.message ??
            "Не удалось сохранить. Проверьте поля и повторите попытку.");
    } finally {
      pending.value = false;
    }
  }
  async function reload() {
    expectedVersion.value = 0;
    error.value = "";
    conflict.value = false;
    await refresh();
    const value = settings.value?.policy;
    if (value) {
      const { version, ...rest } = value;
      Object.assign(policy, rest);
      expectedVersion.value = version;
    }
  }
  async function savePolicy() {
    await action(async () => {
      if (!settings.value?.configured) {
        await initializeMutation.mutateAsync({
          ...policyInput(),
          functional_currency: functional.value,
          valid_from: initialFrom.value,
          enabled_currencies: initialEnabled.value,
          reason: "Первоначальная настройка",
        });
      } else {
        const saved = await policyMutation.mutateAsync({
          ...policyInput(),
          expected_version: expectedVersion.value,
        });
        expectedVersion.value = saved.version;
      }
    });
  }
  function selectInitial(code: string, enabled: boolean) {
    initialEnabled.value = enabled
      ? [...new Set([...initialEnabled.value, code])]
      : initialEnabled.value.filter((c) => c !== code);
  }

  return {
    setManualRate,
    schedulePeriod,
    setEnabledCurrency,
    settingsQuery,
    sourcesQuery,
    sources,
    directoryQuery,
    refresh,
    settings,
    currencies,
    allowed,
    can,
    pending,
    error,
    conflict,
    statusLabels,
    provider,
    offset,
    ratesQuery,
    policy,
    expectedVersion,
    functional,
    initialFrom,
    initialEnabled,
    search,
    visibleCurrencies,
    manual,
    schedule,
    policyInput,
    action,
    reload,
    savePolicy,
    selectInitial,
  };
}
export type CurrencyPageContext = ReturnType<typeof useCurrencyPage>;
