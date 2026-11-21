<script setup lang="ts">
import {
  Field,
  FieldLabel,
  FieldError,
  FieldDescription,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type {
  StockSerialValues,
  StockSerialErrors,
} from "../../model/stock-serial.types";
import type { StockLot } from "../../model/stock-lot.types";
import StockSerialLotPicker from "./StockSerialLotPicker.vue";
const props = defineProps<{
  values: StockSerialValues;
  errors: StockSerialErrors;
  pending: boolean;
  checking: boolean;
  disabled: boolean;
  uncertain: boolean;
  dirty: boolean;
  error: string;
  mode: string;
  lotSearch: string;
  lots: readonly StockLot[];
  lotsLoading: boolean;
  lotsBusy: boolean;
  lotsError: string;
  hasMoreLots: boolean;
  selectedLot?: StockLot;
  selectedLotError: string;
}>();
const emit = defineEmits<{
  change: [values: StockSerialValues];
  submit: [];
  cancel: [];
  verify: [];
  refresh: [];
  searchLots: [value: string];
  moreLots: [];
  retryLots: [];
  retrySelected: [];
  lots: [];
}>();
function change(key: keyof StockSerialValues, value: string): void {
  emit("change", { ...props.values, [key]: value });
}
</script>
<template>
  <section
    class="rounded-md border p-5"
    aria-label="Редактирование серийного экземпляра"
  >
    <h2 class="mb-4 text-lg font-semibold">Редактирование экземпляра</h2>
    <form
      class="flex flex-col gap-4"
      novalidate
      :aria-busy="pending || checking"
      @submit.prevent="emit('submit')"
    >
      <Field :data-invalid="!!errors.number"
        ><FieldLabel for="serial-edit-number">Серийный номер</FieldLabel
        ><Input
          id="serial-edit-number"
          :model-value="values.number"
          :disabled="checking || disabled || uncertain"
          :aria-invalid="!!errors.number"
          aria-describedby="serial-edit-number-hint serial-edit-number-error"
          autocomplete="off"
          autocapitalize="none"
          spellcheck="false"
          @update:model-value="
            change('number', String($event))
          " /><FieldDescription id="serial-edit-number-hint"
          >Регистр и ведущие нули сохраняются.</FieldDescription
        ><FieldError id="serial-edit-number-error" :errors="[errors.number]"
      /></Field>
      <p v-if="mode === 'LOT_AND_SERIAL'" class="text-sm text-muted-foreground">
        После сохранения будут использоваться даты выбранной партии.
      </p>
      <StockSerialLotPicker
        v-if="mode === 'LOT_AND_SERIAL'"
        :search="lotSearch"
        :items="lots"
        :selected-id="values.lotId"
        :selected="selectedLot"
        :selected-error="selectedLotError"
        :loading="lotsLoading"
        :busy="lotsBusy"
        :error="lotsError"
        :has-more="hasMoreLots"
        :disabled="checking || disabled || uncertain"
        @search="emit('searchLots', $event)"
        @select="change('lotId', $event)"
        @more="emit('moreLots')"
        @retry="emit('retryLots')"
        @retry-selected="emit('retrySelected')"
        @lots="emit('lots')"
      />
      <p v-else class="text-sm text-muted-foreground">
        В режиме SERIAL партия и даты отсутствуют.
      </p>
      <Button
        v-if="mode !== 'LOT_AND_SERIAL' && values.lotId"
        type="button"
        variant="outline"
        :disabled="checking || disabled || uncertain"
        @click="change('lotId', '')"
        >Очистить ранее выбранную партию</Button
      >
      <FieldError :errors="[errors.lotId]" />
      <Alert v-if="error" variant="destructive"
        ><AlertDescription>{{ error }}</AlertDescription></Alert
      >
      <Button
        v-if="disabled"
        type="button"
        variant="outline"
        :disabled="pending || checking || uncertain"
        @click="emit('refresh')"
        >Обновить настройки SKU</Button
      >
      <div class="flex flex-wrap justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          :disabled="pending || checking || uncertain"
          @click="emit('cancel')"
          >Отменить изменения</Button
        ><Button
          v-if="uncertain"
          type="button"
          :disabled="pending || checking"
          @click="emit('verify')"
          >Проверить сохранение</Button
        ><Button
          v-else
          type="submit"
          :disabled="pending || checking || disabled || !dirty"
          >{{ pending ? "Сохранение…" : "Сохранить изменения" }}</Button
        >
      </div>
    </form>
  </section>
</template>
