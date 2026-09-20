<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { isAxiosError } from "axios";
import { toast } from "vue-sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import CurrencySelect from "./CurrencySelect.vue";
import { currencyApi } from "../api/currency.api";
import {
  useCurrencyDirectory,
  useCurrencySettings,
  useCurrencyRates,
  useRefreshCurrency,
} from "../model/queries";
import type { PolicyInput } from "../model/types";

const settingsQuery = useCurrencySettings();
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
const schedule = reactive({ currency: "EUR", effective_from: "", reason: "" });
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
      await currencyApi.initialize({
        ...policyInput(),
        functional_currency: functional.value,
        valid_from: initialFrom.value,
        enabled_currencies: initialEnabled.value,
        reason: "Первоначальная настройка",
      });
    } else {
      await currencyApi.configure({
        ...policyInput(),
        expected_version: expectedVersion.value,
      });
      expectedVersion.value += 1;
    }
  });
}
function selectInitial(code: string, enabled: boolean) {
  initialEnabled.value = enabled
    ? [...new Set([...initialEnabled.value, code])]
    : initialEnabled.value.filter((c) => c !== code);
}
</script>

<template>
  <main
    class="mx-auto flex min-h-0 w-full max-w-6xl flex-1 flex-col gap-6 overflow-y-auto p-4 md:p-8"
  >
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div class="flex flex-col gap-2">
        <h1 class="text-2xl font-semibold tracking-tight">Валюты и курсы</h1>
        <p class="text-muted-foreground">
          Валюта учёта, правила пересчёта и история курсов организации.
        </p>
      </div>
      <Button variant="outline" :disabled="pending" @click="reload"
        >Обновить данные</Button
      >
    </header>
    <Alert v-if="error" variant="destructive"
      ><AlertTitle>Изменения не сохранены</AlertTitle
      ><AlertDescription
        >{{ error
        }}<Button v-if="conflict" variant="outline" class="mt-3" @click="reload"
          >Загрузить актуальные данные</Button
        ></AlertDescription
      ></Alert
    >
    <Alert
      v-if="settingsQuery.isError.value || directoryQuery.isError.value"
      variant="destructive"
      ><AlertTitle>Не удалось загрузить валюты</AlertTitle
      ><AlertDescription
        >Проверьте соединение и обновите данные.</AlertDescription
      ></Alert
    >
    <Skeleton
      v-else-if="
        settingsQuery.isPending.value || directoryQuery.isPending.value
      "
      class="h-80 w-full"
    />
    <template v-else-if="settings">
      <Alert v-if="!settings.configured"
        ><AlertTitle>Валютная политика ещё не настроена</AlertTitle
        ><AlertDescription>{{
          can("currency.manage_policy")
            ? "Выберите параметры ниже. До сохранения прайс-листы сохраняют только исходные цены."
            : "Администратор организации должен настроить валютную политику."
        }}</AlertDescription></Alert
      >
      <div v-else class="grid gap-4 sm:grid-cols-3">
        <Card
          ><CardHeader
            ><CardDescription>Основная валюта</CardDescription
            ><CardTitle>{{
              settings.functional_currency ?? "Не действует на сегодня"
            }}</CardTitle></CardHeader
          ><CardContent class="text-sm text-muted-foreground">{{
            settings.future_functional_currency
              ? `Запланирована: ${settings.future_functional_currency}`
              : "Будущих изменений нет"
          }}</CardContent></Card
        >
        <Card
          ><CardHeader
            ><CardDescription>Источник курса</CardDescription
            ><CardTitle>{{
              settings.policy?.provider_code === "MANUAL"
                ? "Ручные курсы"
                : "Национальный банк Украины"
            }}</CardTitle></CardHeader
          ><CardContent class="text-sm text-muted-foreground">{{
            settings.policy?.rate_date_policy === "exact"
              ? "Только точная дата"
              : "Последний доступный курс"
          }}</CardContent></Card
        >
        <Card
          ><CardHeader
            ><CardDescription>Бизнес-дата</CardDescription
            ><CardTitle>{{ settings.business_date }}</CardTitle></CardHeader
          ><CardContent class="text-sm text-muted-foreground">{{
            settings.policy?.business_timezone
          }}</CardContent></Card
        >
      </div>
      <Tabs default-value="policy" class="flex flex-col gap-5">
        <TabsList class="grid h-auto w-full grid-cols-2 sm:inline-flex sm:w-fit"
          ><TabsTrigger
            class="h-auto whitespace-normal text-center"
            value="policy"
            >Политика</TabsTrigger
          ><TabsTrigger
            class="h-auto whitespace-normal text-center"
            value="enabled"
            >Разрешённые валюты</TabsTrigger
          ><TabsTrigger
            class="h-auto whitespace-normal text-center"
            value="rates"
            >Курсы</TabsTrigger
          ><TabsTrigger
            class="h-auto whitespace-normal text-center"
            value="history"
            >История основной валюты</TabsTrigger
          ></TabsList
        >
        <TabsContent value="policy">
          <form @submit.prevent="savePolicy">
            <Card
              ><CardHeader
                ><CardTitle>{{
                  settings.configured
                    ? "Правила конвертации"
                    : "Первоначальная настройка"
                }}</CardTitle
                ><CardDescription
                  >Исходные цены и уже сохранённые валютные снимки останутся в
                  истории.</CardDescription
                ></CardHeader
              >
              <CardContent
                ><fieldset
                  :disabled="pending || !can('currency.manage_policy')"
                >
                  <FieldGroup class="grid gap-5 sm:grid-cols-2">
                    <Field
                      ><FieldLabel for="default-currency"
                        >Валюта новых операций</FieldLabel
                      ><CurrencySelect
                        id="default-currency"
                        v-model="policy.default_transaction_currency"
                        :currencies="
                          settings.configured ? allowed : currencies
                        "
                    /></Field>
                    <Field
                      ><FieldLabel for="provider">Источник курсов</FieldLabel
                      ><NativeSelect
                        id="provider"
                        v-model="policy.provider_code"
                        ><NativeSelectOption value="NBU">НБУ</NativeSelectOption
                        ><NativeSelectOption value="MANUAL"
                          >Ручные курсы</NativeSelectOption
                        ></NativeSelect
                      ></Field
                    >
                    <Field
                      ><FieldLabel for="date-policy">Дата курса</FieldLabel
                      ><NativeSelect
                        id="date-policy"
                        v-model="policy.rate_date_policy"
                        ><NativeSelectOption value="previous_available"
                          >Последний доступный, не позднее
                          даты</NativeSelectOption
                        ><NativeSelectOption value="exact"
                          >Только точная дата</NativeSelectOption
                        ></NativeSelect
                      ></Field
                    >
                    <Field
                      ><FieldLabel for="rounding">Округление</FieldLabel
                      ><NativeSelect
                        id="rounding"
                        v-model="policy.rounding_mode"
                        ><NativeSelectOption value="ROUND_HALF_UP"
                          >Половины вверх</NativeSelectOption
                        ><NativeSelectOption value="ROUND_HALF_EVEN"
                          >Половины к чётному</NativeSelectOption
                        ><NativeSelectOption value="ROUND_DOWN"
                          >К нулю</NativeSelectOption
                        ><NativeSelectOption value="ROUND_UP"
                          >От нуля</NativeSelectOption
                        ></NativeSelect
                      ></Field
                    >
                    <Field
                      ><FieldLabel for="business-timezone"
                        >Часовой пояс организации</FieldLabel
                      ><Input
                        id="business-timezone"
                        v-model="policy.business_timezone"
                        required
                        placeholder="Europe/Kyiv"
                      /><FieldDescription
                        >Определяет календарный день валютных
                        операций.</FieldDescription
                      ></Field
                    >
                    <Field
                      ><FieldLabel for="bridge">Промежуточная валюта</FieldLabel
                      ><CurrencySelect
                        id="bridge"
                        v-model="policy.bridge_currency"
                        :currencies="settings.configured ? allowed : currencies"
                        :disabled="!policy.allow_cross_rate"
                    /></Field>
                    <Field orientation="horizontal"
                      ><Switch
                        id="cross-rate"
                        v-model="policy.allow_cross_rate"
                      /><FieldLabel for="cross-rate"
                        >Разрешить кросс-курс</FieldLabel
                      ></Field
                    >
                    <template v-if="!settings.configured"
                      ><Field
                        ><FieldLabel for="initial-functional"
                          >Основная валюта учёта</FieldLabel
                        ><CurrencySelect
                          id="initial-functional"
                          v-model="functional"
                          :currencies="currencies" /></Field
                      ><Field
                        ><FieldLabel for="initial-from"
                          >Начало первого периода</FieldLabel
                        ><Input
                          id="initial-from"
                          v-model="initialFrom"
                          type="date"
                          required /></Field
                      ><Field
                        ><FieldLabel>Разрешённые валюты</FieldLabel
                        ><FieldDescription
                          >{{ initialEnabled.join(", ") }}. Измените список на
                          соседней вкладке до сохранения.</FieldDescription
                        ></Field
                      ></template
                    >
                  </FieldGroup>
                </fieldset></CardContent
              >
              <CardFooter v-if="can('currency.manage_policy')"
                ><Button type="submit" :disabled="pending || conflict">{{
                  pending
                    ? "Сохранение…"
                    : settings.configured
                      ? "Сохранить политику"
                      : "Настроить валюты"
                }}</Button></CardFooter
              >
            </Card>
          </form>
        </TabsContent>
        <TabsContent value="enabled"
          ><Card
            ><CardHeader
              ><CardTitle>Разрешённые валюты</CardTitle
              ><CardDescription
                >Отключение запрещает новые конвертации. Исторические данные
                остаются доступными.</CardDescription
              ></CardHeader
            ><CardContent class="flex flex-col gap-4">
              <Field
                ><FieldLabel for="currency-search">Найти валюту</FieldLabel
                ><Input
                  id="currency-search"
                  v-model="search"
                  placeholder="Код или название"
              /></Field>
              <div class="max-h-[32rem] overflow-auto">
                <Table
                  ><TableHeader
                    ><TableRow
                      ><TableHead>Код</TableHead><TableHead>Валюта</TableHead
                      ><TableHead>Знаков после запятой</TableHead
                      ><TableHead>Разрешена</TableHead></TableRow
                    ></TableHeader
                  ><TableBody>
                    <TableRow v-if="!visibleCurrencies.length"
                      ><TableCell colspan="4"
                        >Валюты не найдены.</TableCell
                      ></TableRow
                    >
                    <TableRow
                      v-for="currency in visibleCurrencies"
                      :key="currency.code"
                      ><TableCell class="font-medium">{{
                        currency.code
                      }}</TableCell
                      ><TableCell>{{ currency.name }}</TableCell
                      ><TableCell>{{
                        currency.minor_units ?? "Не определено"
                      }}</TableCell
                      ><TableCell
                        ><Switch
                          :aria-label="`Разрешить ${currency.code}`"
                          :model-value="
                            (settings.configured
                              ? settings.enabled_currencies
                              : initialEnabled
                            ).includes(currency.code)
                          "
                          :disabled="pending || !can('currency.manage_enabled')"
                          @update:model-value="
                            settings.configured
                              ? action(() =>
                                  currencyApi.enable(
                                    currency.code,
                                    Boolean($event),
                                  ),
                                )
                              : selectInitial(currency.code, Boolean($event))
                          " /></TableCell
                    ></TableRow> </TableBody
                ></Table>
              </div> </CardContent></Card
        ></TabsContent>
        <TabsContent value="rates" class="flex flex-col gap-5">
          <Card
            ><CardHeader
              ><CardTitle>Загрузка НБУ</CardTitle
              ><CardDescription
                >Официальные курсы загружаются по расписанию. Конвертации
                используют сохранённые данные.</CardDescription
              ></CardHeader
            ><CardContent class="flex flex-wrap items-center gap-4 text-sm"
              ><Badge
                :variant="
                  settings.provider_status.last_import?.status === 'failed'
                    ? 'destructive'
                    : 'secondary'
                "
                >{{
                  statusLabels[
                    settings.provider_status.last_import?.status ?? ""
                  ] ?? "Загрузок ещё не было"
                }}</Badge
              ><span
                >Последняя дата курса:
                {{
                  settings.provider_status.last_available_rate_date ?? "—"
                }}</span
              ><span v-if="settings.provider_status.last_import">{{
                new Date(
                  settings.provider_status.last_import.started_at,
                ).toLocaleString()
              }}</span>
              <p
                v-if="settings.provider_status.last_import?.status === 'failed'"
              >
                Загрузка не завершилась. Обратитесь к администратору сервиса.
              </p></CardContent
            ></Card
          >
          <form
            v-if="settings.configured && can('currency.manage_rates')"
            @submit.prevent="action(() => currencyApi.manual({ ...manual }))"
          >
            <Card
              ><CardHeader
                ><CardTitle>Добавить ручной курс</CardTitle
                ><CardDescription
                  >Исправление создаёт новую ревизию. Курс — количество целевой
                  валюты за одну единицу исходной.</CardDescription
                ></CardHeader
              ><CardContent
                ><FieldGroup class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
                  ><Field
                    ><FieldLabel for="manual-source">Из валюты</FieldLabel
                    ><CurrencySelect
                      id="manual-source"
                      v-model="manual.source_currency"
                      :currencies="allowed" /></Field
                  ><Field
                    ><FieldLabel for="manual-target">В валюту</FieldLabel
                    ><CurrencySelect
                      id="manual-target"
                      v-model="manual.target_currency"
                      :currencies="allowed" /></Field
                  ><Field
                    ><FieldLabel for="manual-rate">Курс</FieldLabel
                    ><Input
                      id="manual-rate"
                      v-model="manual.rate"
                      inputmode="decimal"
                      pattern="[0-9]+(\.[0-9]+)?"
                      placeholder="41.25"
                      required /></Field
                  ><Field
                    ><FieldLabel for="manual-date">Дата действия</FieldLabel
                    ><Input
                      id="manual-date"
                      v-model="manual.effective_date"
                      type="date"
                      required /></Field></FieldGroup></CardContent
              ><CardFooter
                ><Button :disabled="pending">Сохранить курс</Button></CardFooter
              ></Card
            >
          </form>
          <Card
            ><CardHeader><CardTitle>Курсы и ревизии</CardTitle></CardHeader
            ><CardContent class="flex flex-col gap-4"
              ><Field
                ><FieldLabel for="rates-provider">Источник</FieldLabel
                ><NativeSelect id="rates-provider" v-model="provider"
                  ><NativeSelectOption value="NBU">НБУ</NativeSelectOption
                  ><NativeSelectOption value="MANUAL"
                    >Ручные курсы</NativeSelectOption
                  ></NativeSelect
                ></Field
              ><Table
                ><TableHeader
                  ><TableRow
                    ><TableHead>Дата</TableHead><TableHead>Пара</TableHead
                    ><TableHead>Курс</TableHead><TableHead>Ревизия</TableHead
                    ><TableHead>Состояние</TableHead></TableRow
                  ></TableHeader
                ><TableBody
                  ><TableRow v-if="ratesQuery.isPending.value"
                    ><TableCell colspan="5">Загрузка…</TableCell></TableRow
                  ><TableRow v-else-if="ratesQuery.isError.value"
                    ><TableCell colspan="5"
                      >Не удалось загрузить курсы.</TableCell
                    ></TableRow
                  ><TableRow v-else-if="!ratesQuery.data.value?.length"
                    ><TableCell colspan="5"
                      >Курсы пока не загружены.</TableCell
                    ></TableRow
                  ><TableRow
                    v-for="rate in ratesQuery.data.value"
                    :key="rate.id"
                    ><TableCell>{{ rate.effective_date }}</TableCell
                    ><TableCell
                      >{{ rate.pair.source }} →
                      {{ rate.pair.target }}</TableCell
                    ><TableCell class="tabular-nums">{{ rate.rate }}</TableCell
                    ><TableCell>{{ rate.revision }}</TableCell
                    ><TableCell
                      ><Badge
                        :variant="rate.is_current ? 'secondary' : 'outline'"
                        >{{
                          rate.is_current ? "Текущий" : "Исторический"
                        }}</Badge
                      ></TableCell
                    ></TableRow
                  ></TableBody
                ></Table
              ></CardContent
            ><CardFooter class="justify-between"
              ><Button
                variant="outline"
                :disabled="offset === 0 || ratesQuery.isFetching.value"
                @click="offset -= 50"
                >Назад</Button
              ><Button
                variant="outline"
                :disabled="
                  (ratesQuery.data.value?.length ?? 0) < 50 ||
                  ratesQuery.isFetching.value
                "
                @click="offset += 50"
                >Далее</Button
              ></CardFooter
            ></Card
          >
        </TabsContent>
        <TabsContent value="history" class="flex flex-col gap-5"
          ><Card
            ><CardHeader
              ><CardTitle>Периоды основной валюты</CardTitle
              ><CardDescription
                >Прошлые периоды и сохранённые пересчёты не
                меняются.</CardDescription
              ></CardHeader
            ><CardContent
              ><Table
                ><TableHeader
                  ><TableRow
                    ><TableHead>Валюта</TableHead><TableHead>С</TableHead
                    ><TableHead>По</TableHead
                    ><TableHead>Причина</TableHead></TableRow
                  ></TableHeader
                ><TableBody
                  ><TableRow v-if="!settings.periods.length"
                    ><TableCell colspan="4"
                      >Сначала настройте валютную политику.</TableCell
                    ></TableRow
                  ><TableRow v-for="period in settings.periods" :key="period.id"
                    ><TableCell>{{ period.currency }}</TableCell
                    ><TableCell>{{ period.valid_from }}</TableCell
                    ><TableCell>{{
                      period.valid_to ?? "Без окончания"
                    }}</TableCell
                    ><TableCell>{{ period.reason }}</TableCell></TableRow
                  ></TableBody
                ></Table
              ></CardContent
            ></Card
          >
          <form
            v-if="
              settings.configured && can('currency.change_functional_currency')
            "
            @submit.prevent="
              action(() => currencyApi.schedule({ ...schedule }))
            "
          >
            <Card
              ><CardHeader
                ><CardTitle>Запланировать смену</CardTitle
                ><CardDescription
                  >Выберите будущую дату после последнего запланированного
                  периода.</CardDescription
                ></CardHeader
              ><CardContent
                ><FieldGroup class="grid gap-4 sm:grid-cols-2"
                  ><Field
                    ><FieldLabel for="future-currency"
                      >Новая основная валюта</FieldLabel
                    ><CurrencySelect
                      id="future-currency"
                      v-model="schedule.currency"
                      :currencies="allowed" /></Field
                  ><Field
                    ><FieldLabel for="future-from">Дата начала</FieldLabel
                    ><Input
                      id="future-from"
                      v-model="schedule.effective_from"
                      type="date"
                      required /></Field
                  ><Field class="sm:col-span-2"
                    ><FieldLabel for="future-reason">Причина</FieldLabel
                    ><Input
                      id="future-reason"
                      v-model="schedule.reason"
                      maxlength="1000"
                      required /></Field></FieldGroup></CardContent
              ><CardFooter
                ><Button :disabled="pending"
                  >Запланировать смену валюты</Button
                ></CardFooter
              ></Card
            >
          </form>
        </TabsContent>
      </Tabs>
    </template>
  </main>
</template>
