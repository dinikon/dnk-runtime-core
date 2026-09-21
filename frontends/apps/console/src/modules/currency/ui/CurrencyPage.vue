<script setup lang="ts">
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import CurrencyPolicyPanel from "./CurrencyPolicyPanel.vue";
import EnabledCurrenciesPanel from "./EnabledCurrenciesPanel.vue";
import ExchangeRatesPanel from "./ExchangeRatesPanel.vue";
import FunctionalCurrencyHistoryPanel from "./FunctionalCurrencyHistoryPanel.vue";
import { useCurrencyPage } from "../model/use-currency-page";
const context = useCurrencyPage();
const {
  settingsQuery,
  directoryQuery,
  settings,
  can,
  pending,
  error,
  conflict,
  reload,
} = context;
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
    <Alert v-if="error" variant="destructive">
      <AlertTitle>Изменения не сохранены</AlertTitle>
      <AlertDescription>
        {{ error }}
        <Button v-if="conflict" variant="outline" class="mt-3" @click="reload">
          Загрузить актуальные данные
        </Button>
      </AlertDescription></Alert
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
              settings.policy?.provider_code
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
        <TabsList class="grid h-auto w-full grid-cols-2 sm:inline-flex"
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
        <CurrencyPolicyPanel :context="context" />
        <EnabledCurrenciesPanel :context="context" />
        <ExchangeRatesPanel :context="context" />
        <FunctionalCurrencyHistoryPanel :context="context" />
      </Tabs>
    </template>
  </main>
</template>
