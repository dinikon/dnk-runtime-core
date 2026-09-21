<script setup lang="ts">
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { TabsContent } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import CurrencySelect from "./CurrencySelect.vue";
import type { CurrencyPageContext } from "../model/use-currency-page";
const props = defineProps<{ context: CurrencyPageContext }>();
const {
  setManualRate,
  sources,
  settings,
  allowed,
  can,
  pending,
  statusLabels,
  provider,
  offset,
  ratesQuery,
  manual,
  action,
} = props.context;
</script>
<template>
  <template v-if="settings"
    ><TabsContent value="rates" class="flex flex-col gap-5">
      <Card
        ><CardHeader
          ><CardTitle>Загрузка НБУ</CardTitle
          ><CardDescription
            >Официальные курсы загружаются по расписанию. Конвертации используют
            сохранённые данные.</CardDescription
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
            {{ settings.provider_status.last_available_rate_date ?? "—" }}</span
          ><span v-if="settings.provider_status.last_import">{{
            new Date(
              settings.provider_status.last_import.started_at,
            ).toLocaleString()
          }}</span>
          <p v-if="settings.provider_status.last_import?.status === 'failed'">
            Загрузка не завершилась. Обратитесь к администратору сервиса.
          </p></CardContent
        ></Card
      >
      <form
        v-if="settings.configured && can('currency.manage_rates')"
        @submit.prevent="action(() => setManualRate({ ...manual }))"
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
              ><NativeSelectOption
                v-for="source in sources"
                :key="source.code"
                :value="source.code"
                >{{
                  source.local ? "Ручные курсы" : source.code
                }}</NativeSelectOption
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
              ><TableRow v-for="rate in ratesQuery.data.value" :key="rate.id"
                ><TableCell>{{ rate.effective_date }}</TableCell
                ><TableCell
                  >{{ rate.pair.source }} → {{ rate.pair.target }}</TableCell
                ><TableCell class="tabular-nums">{{ rate.rate }}</TableCell
                ><TableCell>{{ rate.revision }}</TableCell
                ><TableCell
                  ><Badge
                    :variant="rate.is_current ? 'secondary' : 'outline'"
                    >{{ rate.is_current ? "Текущий" : "Исторический" }}</Badge
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
    </TabsContent></template
  >
</template>
