<script setup lang="ts">
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { TabsContent } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { CurrencyPageContext } from "../model/use-currency-page";
const props = defineProps<{ context: CurrencyPageContext }>();
const {
  setEnabledCurrency,
  settings,
  can,
  pending,
  initialEnabled,
  search,
  visibleCurrencies,
  action,
  selectInitial,
} = props.context;
</script>
<template>
  <template v-if="settings"
    ><TabsContent value="enabled"
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
                  ><TableCell class="font-medium">{{ currency.code }}</TableCell
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
                              setEnabledCurrency(
                                currency.code,
                                Boolean($event),
                              ),
                            )
                          : selectInitial(currency.code, Boolean($event))
                      " /></TableCell
                ></TableRow> </TableBody
            ></Table>
          </div> </CardContent></Card></TabsContent
  ></template>
</template>
