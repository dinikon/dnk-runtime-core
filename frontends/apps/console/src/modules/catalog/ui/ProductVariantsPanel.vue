<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useSkus } from "@/modules/inventory";
import { catalogApi } from "../api/catalog.api";
import type { ProductDto } from "../api/contracts";
import { catalogError } from "../model/forms";
import { useUnsavedChanges } from "@/shared/model/use-unsaved-changes";
import { productKey, useCatalogTenant } from "../model/queries";
import RequestError from "./RequestError.vue";

const props = defineProps<{
  product: ProductDto;
  locale: string;
  editable: boolean;
}>();
const client = useQueryClient();
const tenant = useCatalogTenant();
const skus = useSkus();
const options = computed(() => {
  const values = new Map(
    (skus.data.value?.pages.flat() ?? []).map((item) => [
      item.id,
      { id: item.id, code: item.code },
    ]),
  );
  for (const item of props.product.variants)
    if (!values.has(item.sku_id))
      values.set(item.sku_id, { id: item.sku_id, code: item.sku_code });
  return [...values.values()];
});
const selectedId = ref("");
const selected = computed(
  () =>
    props.product.variants.find((item) => item.id === selectedId.value) ??
    props.product.variants[0],
);
const skuDraft = ref("");
const newSku = ref("");
const description = ref("");
const busy = ref(false);
const error = ref("");
const dirty = computed(
  () =>
    !!selected.value &&
    (skuDraft.value !== selected.value.sku_id ||
      description.value !== (selected.value.short_description ?? "")),
);
useUnsavedChanges(dirty, busy);
function chooseVariant(id: string) {
  if (
    dirty.value &&
    !window.confirm("Изменения варианта не сохранены. Переключиться?")
  )
    return;
  selectedId.value = id;
}
watch(
  [selected, () => props.locale],
  ([item]) => {
    if (!item) return;
    selectedId.value = item.id;
    skuDraft.value = item.sku_id;
    description.value = item.short_description ?? "";
  },
  { immediate: true },
);
async function run(task: () => Promise<unknown>, success: string) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    await task();
    await client.invalidateQueries({
      queryKey: productKey(tenant.value, props.product.id),
    });
    toast.success(success);
  } catch (reason) {
    error.value = catalogError(reason);
  } finally {
    busy.value = false;
  }
}
function add() {
  if (
    !newSku.value ||
    props.product.variants.some((item) => item.sku_id === newSku.value)
  ) {
    error.value = "Выберите другой SKU для нового варианта.";
    return;
  }
  if (props.product.kind === "simple") {
    void run(
      () =>
        catalogApi.putVariantStructure(props.product.id, {
          kind: "variable",
          variants: [
            {
              id: props.product.variants[0]!.id,
              sku_id: props.product.variants[0]!.sku_id,
            },
            { sku_id: newSku.value },
          ],
        }),
      "Товар стал вариативным",
    );
  } else {
    void run(
      () => catalogApi.createVariant(props.product.id, newSku.value),
      "Вариант создан",
    );
  }
  newSku.value = "";
}
function changeSku() {
  if (
    !selected.value ||
    !skuDraft.value ||
    skuDraft.value === selected.value.sku_id
  )
    return;
  void run(
    () =>
      catalogApi.putVariant(
        props.product.id,
        selected.value!.id,
        skuDraft.value,
      ),
    "SKU варианта обновлён",
  );
}
function saveContent() {
  if (!selected.value || !props.editable || !description.value.trim()) {
    error.value =
      "Для перевода варианта нужен непустой текст и активная локаль.";
    return;
  }
  void run(
    () =>
      catalogApi.putVariantContent(
        props.product.id,
        selected.value!.id,
        props.locale,
        description.value,
      ),
    "Перевод варианта сохранён",
  );
}
function remove() {
  if (
    !selected.value ||
    props.product.variants.length <= 2 ||
    !window.confirm("Удалить вариант и его переводы?")
  )
    return;
  void run(
    () => catalogApi.deleteVariant(props.product.id, selected.value!.id),
    "Вариант удалён",
  );
}
function makeSimple() {
  if (
    !selected.value ||
    !window.confirm(
      "Оставить только выбранный вариант? Остальные варианты и их переводы будут удалены.",
    )
  )
    return;
  void run(
    () =>
      catalogApi.putVariantStructure(props.product.id, {
        kind: "simple",
        variants: [{ id: selected.value!.id, sku_id: selected.value!.sku_id }],
      }),
    "Товар стал простым",
  );
}
</script>

<template>
  <Card>
    <CardHeader
      ><CardTitle>Варианты</CardTitle
      ><CardDescription
        >Каждый вариант ссылается на SKU в Inventory. Выберите позицию, чтобы
        изменить её данные.</CardDescription
      ></CardHeader
    >
    <CardContent
      class="grid gap-6 lg:grid-cols-[minmax(220px,1fr)_minmax(260px,2fr)]"
    >
      <div class="space-y-2">
        <button
          v-for="item in product.variants"
          :key="item.id"
          type="button"
          class="w-full rounded-lg border p-3 text-left text-sm hover:bg-muted/40"
          :class="selected?.id === item.id ? 'border-primary bg-muted/40' : ''"
          @click="chooseVariant(item.id)"
        >
          <span class="font-medium">{{ item.sku_code }}</span
          ><span class="block text-xs text-muted-foreground">{{
            item.short_description ?? "Нет перевода для выбранного языка"
          }}</span>
        </button>
        <div class="flex gap-2">
          <Select
            :model-value="newSku"
            @update:model-value="newSku = String($event ?? '')"
            ><SelectTrigger class="w-full"
              ><SelectValue placeholder="SKU нового варианта" /></SelectTrigger
            ><SelectContent
              ><SelectGroup
                ><SelectItem
                  v-for="item in options"
                  :key="item.id"
                  :value="item.id"
                  >{{ item.code }}</SelectItem
                ></SelectGroup
              ></SelectContent
            ></Select
          ><Button type="button" :disabled="busy || !newSku" @click="add"
            >Добавить</Button
          >
        </div>
        <Button
          v-if="skus.hasNextPage.value"
          variant="outline"
          type="button"
          :disabled="skus.isFetching.value"
          @click="skus.fetchNextPage()"
          >Загрузить ещё SKU</Button
        >
      </div>
      <div v-if="selected" class="space-y-4">
        <p class="text-xs text-muted-foreground">
          ID варианта: {{ selected.id }}
        </p>
        <div class="flex gap-2">
          <Select
            :model-value="skuDraft"
            @update:model-value="skuDraft = String($event ?? '')"
            ><SelectTrigger class="w-full"
              ><SelectValue placeholder="SKU" /></SelectTrigger
            ><SelectContent
              ><SelectGroup
                ><SelectItem
                  v-for="item in options"
                  :key="item.id"
                  :value="item.id"
                  >{{ item.code }}</SelectItem
                ></SelectGroup
              ></SelectContent
            ></Select
          ><Button
            variant="outline"
            type="button"
            :disabled="busy || skuDraft === selected.sku_id"
            @click="changeSku"
            >Сохранить SKU</Button
          >
        </div>
        <div>
          <label class="mb-2 block text-sm font-medium"
            >Описание варианта · {{ locale }}</label
          ><Textarea
            v-model="description"
            :disabled="busy || !editable"
            rows="4"
          /><Button
            class="mt-2"
            type="button"
            :disabled="busy || !editable || !description.trim()"
            @click="saveContent"
            >Сохранить перевод</Button
          >
        </div>
        <div class="flex flex-wrap gap-2">
          <Button
            v-if="product.kind === 'variable' && product.variants.length > 2"
            variant="destructive"
            type="button"
            :disabled="busy"
            @click="remove"
            >Удалить вариант</Button
          ><Button
            v-if="product.kind === 'variable'"
            variant="outline"
            type="button"
            :disabled="busy"
            @click="makeSimple"
            >Оставить один вариант</Button
          >
        </div>
        <RequestError v-if="error" :message="error" />
      </div>
    </CardContent>
  </Card>
</template>
