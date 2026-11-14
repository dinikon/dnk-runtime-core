<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { CounterpartyReference } from "@/modules/crm";
import type {
  SourceValues,
  SourceFieldErrors,
} from "../../model/supplier-source.types";
import SupplierSourceForm from "./SupplierSourceForm.vue";
import SupplierCounterpartyPicker from "./SupplierCounterpartyPicker.vue";
defineProps<{
  open: boolean;
  values: SourceValues;
  errors: SourceFieldErrors;
  pending: boolean;
  disabled: boolean;
  error: string;
  uncertain: boolean;
  counterpartySearch: string;
  counterparties: readonly CounterpartyReference[];
  selectedCounterparty: CounterpartyReference | null;
  counterpartiesLoading: boolean;
  counterpartiesError: string;
  counterpartiesOffset: number;
  counterpartiesTotal: number;
}>();
const emit = defineEmits<{
  close: [];
  change: [values: SourceValues];
  submit: [];
  check: [];
  counterpartySearch: [value: string];
  counterpartySelect: [value: CounterpartyReference];
  counterpartyPage: [offset: number];
  counterpartyRetry: [];
}>();
</script>
<template>
  <Dialog :open="open" @update:open="!$event && !pending && emit('close')"
    ><DialogContent
      class="max-h-[90dvh] overflow-y-auto sm:max-w-xl"
      :show-close-button="!pending"
      @escape-key-down="pending && $event.preventDefault()"
      @interact-outside="pending && $event.preventDefault()"
      ><DialogHeader
        ><DialogTitle>Создать источник</DialogTitle
        ><DialogDescription
          >Выберите контрагента CRM и задайте настройки поставки. Новый источник
          будет активным.</DialogDescription
        ></DialogHeader
      >
      <form
        class="flex flex-col gap-5"
        novalidate
        :aria-busy="pending"
        @submit.prevent="emit('submit')"
      >
        <label
          class="flex min-w-0 flex-col gap-2 text-sm font-medium [&_[data-slot=native-select-wrapper]]:w-full"
          >Тип поставщика
          <NativeSelect
            aria-label="Тип поставщика"
            :model-value="values.supplierModelKey"
            :disabled="disabled || pending || uncertain"
            @update:model-value="
              emit('change', {
                ...values,
                supplierModelKey:
                  $event === 'crm.contact' ? 'crm.contact' : 'crm.company',
                supplierId: '',
              })
            "
          >
            <NativeSelectOption value="crm.company"
              >Компания</NativeSelectOption
            >
            <NativeSelectOption value="crm.contact">Контакт</NativeSelectOption>
          </NativeSelect>
        </label>
        <SupplierCounterpartyPicker
          :search="counterpartySearch"
          :items="counterparties"
          :selected="selectedCounterparty"
          :loading="counterpartiesLoading"
          :error="counterpartiesError"
          :offset="counterpartiesOffset"
          :total="counterpartiesTotal"
          :disabled="disabled || pending || uncertain"
          @search="emit('counterpartySearch', $event)"
          @select="emit('counterpartySelect', $event)"
          @page="emit('counterpartyPage', $event)"
          @retry="emit('counterpartyRetry')"
        />
        <p
          v-if="errors.supplierId"
          role="alert"
          class="text-sm text-destructive"
        >
          {{ errors.supplierId }}
        </p>
        <SupplierSourceForm
          :values="values"
          :errors="errors"
          :disabled="disabled || pending || uncertain"
          :editing="false"
          @change="emit('change', $event)"
        /><Alert v-if="error" variant="destructive"
          ><AlertDescription>{{ error }}</AlertDescription></Alert
        >
        <div class="flex flex-wrap gap-2">
          <Button type="submit" :disabled="disabled || pending || uncertain">{{
            pending ? "Создание…" : "Создать источник"
          }}</Button
          ><Button
            v-if="uncertain"
            type="button"
            variant="outline"
            @click="emit('check')"
            >Проверить список</Button
          ><Button
            type="button"
            variant="outline"
            :disabled="pending"
            @click="emit('close')"
            >Отмена</Button
          >
        </div>
      </form>
    </DialogContent></Dialog
  >
</template>
