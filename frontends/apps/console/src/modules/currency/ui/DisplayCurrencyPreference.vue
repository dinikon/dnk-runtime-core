<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { useCurrentUserQuery } from "@/modules/auth/queries/use-current-user-query";
import { authQueryKeys } from "@/modules/auth/model/auth.query-keys";
import { useCurrencySettings, useCurrencyDirectory } from "../model/queries";
import { saveDisplayCurrency } from "../api/display-currency.api";
import { getApiErrorMessage } from "@/app/providers/http";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Field, FieldLabel, FieldDescription } from "@/components/ui/field";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
const user = useCurrentUserQuery();
const settings = useCurrencySettings();
const directory = useCurrencyDirectory();
const client = useQueryClient();
const selection = ref("inherit");
watch(
  () => user.data.value?.display_currency,
  (value) => {
    selection.value = value ?? "inherit";
  },
  { immediate: true },
);
const choices = computed(() =>
  (directory.data.value ?? []).filter((c) =>
    settings.data.value?.enabled_currencies.includes(c.code),
  ),
);
const unavailable = computed(
  () =>
    selection.value !== "inherit" &&
    !choices.value.some((c) => c.code === selection.value),
);
const save = useMutation({
  mutationFn: () =>
    saveDisplayCurrency(selection.value === "inherit" ? null : selection.value),
  onSuccess: async () => {
    await client.invalidateQueries({ queryKey: authQueryKeys.currentUser() });
    await client.invalidateQueries({
      predicate: (q) => q.queryKey.includes("offers"),
    });
  },
});
</script>
<template>
  <Card class="max-w-2xl"
    ><CardHeader
      ><CardTitle>Валюта интерфейса</CardTitle
      ><CardDescription
        >Личная настройка отображения текущих сумм. Исторические цены
        сохраняются в валюте учёта.</CardDescription
      ></CardHeader
    >
    <CardContent
      ><Field
        ><FieldLabel for="profile-display-currency"
          >Валюта отображения</FieldLabel
        >
        <NativeSelect
          id="profile-display-currency"
          v-model="selection"
          :disabled="
            save.isPending.value ||
            user.isPending.value ||
            settings.isPending.value
          "
        >
          <NativeSelectOption value="inherit"
            >По умолчанию организации —
            {{
              settings.data.value?.default_display_currency ?? "не настроена"
            }}</NativeSelectOption
          >
          <NativeSelectOption v-if="unavailable" :value="selection"
            >{{ selection }} — недоступна</NativeSelectOption
          >
          <NativeSelectOption
            v-for="currency in choices"
            :key="currency.code"
            :value="currency.code"
            >{{ currency.code }} · {{ currency.name
            }}{{
              currency.code === settings.data.value?.default_display_currency
                ? " · по умолчанию организации"
                : ""
            }}</NativeSelectOption
          > </NativeSelect
        ><FieldDescription
          >При наследовании значение обновится вместе с настройкой
          организации.</FieldDescription
        > </Field
      ><Alert v-if="unavailable" class="mt-4"
        ><AlertDescription
          >Выбранная валюта отключена. Выберите доступную валюту или значение
          организации.</AlertDescription
        ></Alert
      >
      <Alert
        v-if="
          save.isError.value ||
          user.isError.value ||
          settings.isError.value ||
          directory.isError.value
        "
        class="mt-4"
        variant="destructive"
        ><AlertDescription>{{
          save.error.value
            ? getApiErrorMessage(
                save.error.value,
                "Не удалось сохранить валюту.",
              )
            : "Не удалось загрузить настройки валют."
        }}</AlertDescription></Alert
      >
      <p v-if="save.isSuccess.value" role="status" class="mt-4 text-sm">
        Валюта отображения сохранена.
      </p></CardContent
    >
    <CardFooter
      ><Button
        :disabled="
          save.isPending.value ||
          unavailable ||
          user.isPending.value ||
          settings.isPending.value
        "
        @click="save.mutate()"
        >Сохранить валюту</Button
      ></CardFooter
    >
  </Card>
</template>
