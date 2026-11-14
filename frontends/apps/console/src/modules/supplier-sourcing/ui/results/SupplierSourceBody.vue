<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import type {
  SupplierSource,
  SourceValues,
  SourceFieldErrors,
} from "../../model/supplier-source.types";
import SupplierSourceForm from "../forms/SupplierSourceForm.vue";
defineProps<{
  source: SupplierSource | undefined;
  values: SourceValues | null;
  errors: SourceFieldErrors;
  ready: boolean;
  pending: boolean;
  dirty: boolean;
  error: string;
  saveError: string;
  saved: boolean;
  loading: boolean;
  refreshing: boolean;
}>();
const emit = defineEmits<{
  submit: [];
  reset: [];
  retry: [];
  change: [value: SourceValues];
}>();
import { supplierTypeLabels } from "../../model/supplier-source.constants";
</script>
<template>
  <div class="flex min-w-0 flex-col gap-5">
    <Alert v-if="error" variant="destructive"
      ><AlertDescription
        >{{ error }}
        <Button
          variant="outline"
          size="sm"
          :disabled="!ready || refreshing"
          @click="emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    ><Skeleton v-if="loading && !error" class="h-64 w-full" /><template
      v-if="values && source"
      ><div class="max-w-2xl rounded-lg border p-4 text-sm">
        <span class="mr-1 text-muted-foreground">Поставщик:</span>
        <strong>{{ source.supplierName ?? source.supplierId }}</strong>
        <span class="ml-1 text-muted-foreground"
          >· {{ supplierTypeLabels[source.supplierModelKey] }}</span
        >
        <p class="mt-1 text-muted-foreground">
          Контрагент задаётся при создании и не меняется в редакторе.
        </p>
      </div>
      <form
        class="flex max-w-2xl flex-col gap-5 rounded-lg border p-4 sm:p-6"
        novalidate
        :aria-busy="pending"
        @submit.prevent="emit('submit')"
      >
        <SupplierSourceForm
          :values="values"
          :errors="errors"
          :disabled="!ready || pending"
          :editing="true"
          @change="emit('change', $event)"
        /><Alert v-if="saveError" variant="destructive"
          ><AlertDescription>{{ saveError }}</AlertDescription></Alert
        >
        <p v-if="saved" role="status" class="text-sm text-muted-foreground">
          Изменения сохранены.
        </p>
        <div class="flex flex-wrap gap-2">
          <Button type="submit" :disabled="!ready || pending || !dirty">{{
            pending ? "Сохранение…" : "Сохранить"
          }}</Button
          ><Button
            type="button"
            variant="outline"
            :disabled="pending || !dirty"
            @click="emit('reset')"
            >Сбросить изменения</Button
          ><Button
            type="button"
            variant="ghost"
            :disabled="pending || !ready || refreshing"
            @click="emit('retry')"
            >Обновить карточку</Button
          >
        </div>
      </form></template
    >
  </div>
</template>
