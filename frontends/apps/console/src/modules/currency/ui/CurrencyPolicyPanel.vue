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
import { TabsContent } from "@/components/ui/tabs";
import CurrencySelect from "./CurrencySelect.vue";
import type { CurrencyPageContext } from "../model/use-currency-page";
const props = defineProps<{ context: CurrencyPageContext }>();
const {
  sources,
  settings,
  currencies,
  allowed,
  can,
  pending,
  conflict,
  policy,
  functional,
  initialFrom,
  initialEnabled,
  savePolicy,
} = props.context;
</script>
<template>
  <template v-if="settings"
    ><TabsContent value="policy">
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
            ><fieldset :disabled="pending || !can('currency.manage_policy')">
              <FieldGroup class="grid gap-5 sm:grid-cols-2">
                <Field
                  ><FieldLabel for="default-currency"
                    >Валюта новых операций</FieldLabel
                  ><CurrencySelect
                    id="default-currency"
                    v-model="policy.default_transaction_currency"
                    :currencies="settings.configured ? allowed : currencies"
                /></Field>
                <Field
                  ><FieldLabel for="provider">Источник курсов</FieldLabel
                  ><NativeSelect id="provider" v-model="policy.provider_code"
                    ><NativeSelectOption
                      v-for="source in sources"
                      :key="source.code"
                      :value="source.code"
                      >{{
                        source.local ? "Ручные курсы" : source.code
                      }}</NativeSelectOption
                    ></NativeSelect
                  ></Field
                >
                <Field
                  ><FieldLabel for="date-policy">Дата курса</FieldLabel
                  ><NativeSelect
                    id="date-policy"
                    v-model="policy.rate_date_policy"
                    ><NativeSelectOption value="previous_available"
                      >Последний доступный, не позднее даты</NativeSelectOption
                    ><NativeSelectOption value="exact"
                      >Только точная дата</NativeSelectOption
                    ></NativeSelect
                  ></Field
                >
                <Field
                  ><FieldLabel for="rounding">Округление</FieldLabel
                  ><NativeSelect id="rounding" v-model="policy.rounding_mode"
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
                  ><FieldLabel for="default-display-currency"
                    >Валюта интерфейса организации</FieldLabel
                  >
                  <NativeSelect
                    id="default-display-currency"
                    :model-value="policy.default_display_currency ?? 'inherit'"
                    @update:model-value="
                      policy.default_display_currency =
                        $event === 'inherit' ? null : String($event)
                    "
                  >
                    <NativeSelectOption value="inherit"
                      >Основная валюта организации{{
                        settings?.functional_currency
                          ? ` — ${settings.functional_currency}`
                          : ""
                      }}</NativeSelectOption
                    >
                    <NativeSelectOption
                      v-for="currency in settings?.configured
                        ? allowed
                        : currencies.filter((c) =>
                            initialEnabled.includes(c.code),
                          )"
                      :key="currency.code"
                      :value="currency.code"
                      >{{ currency.code }} ·
                      {{ currency.name }}</NativeSelectOption
                    > </NativeSelect
                  ><FieldDescription
                    >Используется пользователями без личного выбора
                    валюты.</FieldDescription
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
    </TabsContent></template
  >
</template>
