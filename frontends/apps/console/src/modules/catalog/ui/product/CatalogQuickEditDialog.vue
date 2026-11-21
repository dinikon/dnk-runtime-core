<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import type { CatalogItem } from "../../model/catalog.types";
import type { CatalogQuickEditSection } from "../../model/catalog-table.types";
import type { ProductPatch } from "../../model/product.types";
import { sectionError } from "../../model/product-validation";
import { clone } from "../../model/clone";
import ProductPricingForm from "../forms/ProductPricingForm.vue";
import ProductStockForm from "../forms/ProductStockForm.vue";
import "./product.css";

const props = defineProps<{
  item: CatalogItem | null;
  section: CatalogQuickEditSection;
  shared: boolean;
  loading: boolean;
  pending: boolean;
  error: string;
  blocked: boolean;
}>();
const emit = defineEmits<{
  close: [];
  retry: [];
  save: [patch: ProductPatch];
  dirty: [value: boolean];
}>();
const draft = ref<ProductPatch>({}),
  dirty = ref(false),
  submitted = ref(false);
watch(
  () => props.item,
  (item) => {
    if (item && !dirty.value)
      draft.value =
        props.section === "price"
          ? { price_specification: clone(item.price_specification) }
          : { stock: clone(item.stock) };
  },
  { immediate: true },
);
const validation = computed(() =>
  props.section === "price" && !draft.value.price_specification
    ? "Укажите цену и валюту."
    : sectionError(props.section, draft.value),
);
function change(patch: ProductPatch): void {
  draft.value = patch;
  dirty.value = true;
  emit("dirty", true);
}
function save(): void {
  submitted.value = true;
  if (!validation.value && dirty.value) emit("save", clone(draft.value));
}
</script>
<template>
  <Dialog :open="true" @update:open="!$event && !pending && emit('close')">
    <DialogContent
      class="product-editor max-h-[90dvh] overflow-y-auto sm:max-w-md"
      :show-close-button="!pending"
      @escape-key-down="pending && $event.preventDefault()"
      @interact-outside="$event.preventDefault()"
    >
      <DialogHeader>
        <DialogTitle>{{
          section === "price"
            ? "Изменить цену"
            : shared || item?.kind === "variable"
              ? "Изменить общий остаток"
              : "Изменить остаток"
        }}</DialogTitle>
        <DialogDescription
          >{{ item?.title ?? "Загрузка товара…"
          }}{{
            shared || item?.kind === "variable"
              ? ". Изменение общего остатка затронет все варианты, использующие его."
              : ""
          }}</DialogDescription
        >
      </DialogHeader>
      <p
        v-if="loading"
        role="status"
        class="flex items-center gap-2 text-sm text-muted-foreground"
      >
        <Spinner />Загружаем актуальные данные…
      </p>
      <Alert v-if="error" variant="destructive"
        ><AlertDescription
          >{{ error
          }}<Button
            v-if="!item || blocked"
            type="button"
            variant="outline"
            :disabled="loading"
            @click="emit('retry')"
            >Повторить</Button
          ></AlertDescription
        ></Alert
      >
      <form
        v-if="item"
        novalidate
        id="catalog-quick-edit"
        class="product-editor flex flex-col gap-4"
        @submit.prevent="save"
      >
        <ProductPricingForm
          v-if="section === 'price'"
          id="quick"
          :value="draft.price_specification ?? null"
          :reset="0"
          :disabled="pending || loading || blocked"
          :current="item.price"
          :error="submitted ? validation : ''"
          @change="change({ price_specification: $event })"
        />
        <ProductStockForm
          v-else
          id="quick"
          :value="draft.stock ?? item.stock"
          :kind="item.kind"
          :reset="0"
          :disabled="pending || loading || blocked"
          :current="item.stock_status"
          :error="submitted ? validation : ''"
          @change="change({ stock: $event })"
        />
      </form>
      <DialogFooter>
        <Button
          type="button"
          variant="outline"
          :disabled="pending"
          @click="emit('close')"
          >Отмена</Button
        >
        <Button
          type="submit"
          form="catalog-quick-edit"
          :disabled="!item || !dirty || pending || loading || blocked"
          >{{ pending ? "Сохраняем…" : "Сохранить" }}</Button
        >
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
