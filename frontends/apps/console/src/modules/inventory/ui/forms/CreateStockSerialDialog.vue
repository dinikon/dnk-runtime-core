<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
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
  open: boolean;
  sku: string;
  values: StockSerialValues;
  errors: StockSerialErrors;
  pending: boolean;
  disabled: boolean;
  uncertain: boolean;
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
  close: [];
  change: [values: StockSerialValues];
  submit: [];
  check: [];
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
  <Dialog :open="open" @update:open="!$event && !pending && emit('close')"
    ><DialogContent
      class="max-h-[calc(100dvh-2rem)] overflow-y-auto"
      :show-close-button="!pending"
      @escape-key-down="pending && $event.preventDefault()"
      @interact-outside="pending && $event.preventDefault()"
    >
      <DialogHeader
        ><DialogTitle>Создать серийный экземпляр</DialogTitle
        ><DialogDescription class="break-words"
          >SKU: {{ sku }}. Укажите серийный номер<span
            v-if="mode === 'LOT_AND_SERIAL'"
          >
            и партию того же товара</span
          >.</DialogDescription
        ></DialogHeader
      >
      <form
        class="flex flex-col gap-4"
        novalidate
        :aria-busy="pending"
        @submit.prevent="emit('submit')"
      >
        <Field :data-invalid="!!errors.number"
          ><FieldLabel for="serial-number">Серийный номер</FieldLabel
          ><Input
            id="serial-number"
            :model-value="values.number"
            :disabled="pending || disabled || uncertain"
            :aria-invalid="!!errors.number"
            aria-describedby="serial-number-hint serial-number-error"
            autocomplete="off"
            autocapitalize="none"
            spellcheck="false"
            @update:model-value="
              change('number', String($event))
            " /><FieldDescription id="serial-number-hint"
            >Регистр и ведущие нули сохраняются.</FieldDescription
          ><FieldError id="serial-number-error" :errors="[errors.number]"
        /></Field>
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
          :disabled="pending || disabled || uncertain"
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
          :disabled="pending || uncertain"
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
          :disabled="pending"
          @click="emit('refresh')"
          >Обновить настройки SKU</Button
        >
        <DialogFooter class="flex-wrap gap-2"
          ><Button
            type="button"
            variant="outline"
            :disabled="pending"
            @click="emit('close')"
            >Отмена</Button
          ><Button
            v-if="uncertain"
            type="button"
            :disabled="pending || disabled"
            @click="emit('check')"
            >Проверить список</Button
          ><Button v-else type="submit" :disabled="pending || disabled">{{
            pending ? "Создание…" : "Создать"
          }}</Button></DialogFooter
        >
      </form>
    </DialogContent></Dialog
  >
</template>
