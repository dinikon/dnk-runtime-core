<script setup lang="ts">
import { FieldGroup } from "@/components/ui/field";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import StockLotDatesFields from "./StockLotDatesFields.vue";
import type {
  StockLotDatesValues,
  StockLotDatesErrors,
} from "../../model/stock-lot.types";
defineProps<{
  number: string;
  values: StockLotDatesValues;
  errors: StockLotDatesErrors;
  pending: boolean;
  checking: boolean;
  disabled: boolean;
  uncertain: boolean;
  dirty: boolean;
  error: string;
  expirationMode: string;
}>();
const emit = defineEmits<{
  change: [value: StockLotDatesValues];
  submit: [];
  reset: [];
  verify: [];
}>();
</script>
<template>
  <form
    class="flex flex-col gap-5 rounded-md border p-5"
    novalidate
    :aria-busy="pending || checking"
    @submit.prevent="emit('submit')"
  >
    <div class="min-w-0">
      <p class="text-sm text-muted-foreground">Номер партии</p>
      <p class="break-all font-mono">{{ number }}</p>
    </div>
    <FieldGroup
      ><StockLotDatesFields
        id-prefix="lot-edit"
        :values="values"
        :errors="errors"
        :disabled="disabled || checking"
        :expiration-mode="expirationMode"
        @change="emit('change', $event)"
    /></FieldGroup>
    <Alert v-if="error" variant="destructive"
      ><AlertDescription>{{ error }}</AlertDescription></Alert
    >
    <div class="flex flex-wrap gap-2">
      <Button
        v-if="uncertain"
        type="button"
        :disabled="pending || checking"
        @click="emit('verify')"
        >{{ checking ? "Проверка…" : "Проверить сохранение" }}</Button
      >
      <Button
        v-else
        type="submit"
        :disabled="disabled || pending || checking || !dirty"
        >{{ pending ? "Сохранение…" : "Сохранить даты" }}</Button
      >
      <Button
        type="button"
        variant="outline"
        :disabled="pending || checking || !dirty || uncertain"
        @click="emit('reset')"
        >Сбросить изменения</Button
      >
    </div>
  </form>
</template>
