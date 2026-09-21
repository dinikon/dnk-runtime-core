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
import { TabsContent } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import CurrencySelect from "./CurrencySelect.vue";
import type { CurrencyPageContext } from "../model/use-currency-page";
const props = defineProps<{ context: CurrencyPageContext }>();
const { schedulePeriod, settings, allowed, can, pending, schedule, action } =
  props.context;
</script>
<template>
  <template v-if="settings"
    ><TabsContent value="history" class="flex flex-col gap-5"
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
                ><TableCell>{{ period.valid_to ?? "Без окончания" }}</TableCell
                ><TableCell>{{ period.reason }}</TableCell></TableRow
              ></TableBody
            ></Table
          ></CardContent
        ></Card
      >
      <form
        v-if="settings.configured && can('currency.change_functional_currency')"
        @submit.prevent="action(() => schedulePeriod({ ...schedule }))"
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
    </TabsContent></template
  >
</template>
