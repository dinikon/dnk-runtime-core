<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { getApiErrorMessage } from "@/app/providers/http";
import { useProductPage } from "../../model/use-product-page";
import { useProductEditorPageState } from "../../model/use-product-editor-page-state";
import type { ProductSection } from "../../model/product.types";
import CatalogVariantsPage from "./CatalogVariantsPage.vue";
import ProductHeader from "../product/ProductHeader.vue";
import ProductEditor from "../product/ProductEditor.vue";
const {
  ctx,
  id,
  scope,
  item,
  schema,
  pending,
  error,
  blocked,
  isDirty,
  save,
  upload,
  reload,
  imageUrl,
  fieldError,
  saveStatus,
  retry,
  uploading,
  resets,
  contentValues,
  changeContent,
  flush,
} = useProductPage();
const pageState = useProductEditorPageState(
  () => item.data.value?.kind === "variable",
);
const sections: ProductSection[] = [
  "content",
  "status",
  "sku",
  "virtual",
  "price",
  "stock",
  "measurements",
  "galleries",
];
const errors = computed(() =>
  Object.fromEntries(sections.map((s) => [s, fieldError(s)])),
);
const dirty = computed(() => sections.filter(isDirty));
function focused(): void {
  const query = { ...ctx.route.query };
  delete query.focus;
  void ctx.router.replace({ query });
}
</script>
<template>
  <div
    class="product-editor -mx-4 -mb-4 flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto bg-background lg:overflow-hidden"
  >
    <Teleport to="#workspace-page-header" defer>
      <ProductHeader
        :title="
          contentValues.title || item.data.value?.title || 'Товар без названия'
        "
        :locale="ctx.locale.value"
        :options="ctx.options.value"
        @back="
          ctx.router.push({
            path: '/catalog/items',
            query: { locale: ctx.locale.value },
          })
        "
        @locale="ctx.selectLocale"
      />
    </Teleport>
    <div
      v-if="
        item.isError.value ||
        schema.isError.value ||
        (!ctx.active.value && !ctx.locales.isPending.value)
      "
      class="flex shrink-0 flex-col gap-3 p-4"
    >
      <Alert
        v-if="item.isError.value || schema.isError.value"
        variant="destructive"
      >
        <AlertTitle>{{
          item.isError.value
            ? "Не удалось открыть товар"
            : "Не удалось загрузить поля контента"
        }}</AlertTitle>
        <AlertDescription
          >{{
            getApiErrorMessage(
              item.error.value || schema.error.value,
              "Повторите загрузку.",
            )
          }}<Button
            type="button"
            variant="outline"
            :disabled="pending"
            @click="reload"
            >Повторить загрузку</Button
          ></AlertDescription
        >
      </Alert>
      <Alert v-if="!ctx.active.value && !ctx.locales.isPending.value"
        ><AlertTitle>Редактирование недоступно</AlertTitle
        ><AlertDescription
          >Выберите активный язык каталога. Сохранённые значения доступны для
          просмотра.</AlertDescription
        ></Alert
      >
    </div>
    <div
      v-if="item.isPending.value"
      role="status"
      aria-label="Загрузка товара"
      class="grid flex-1 gap-6 p-5 lg:grid-cols-[340px_1fr]"
    >
      <Skeleton class="h-96 w-full" /><Skeleton class="h-72 w-full" />
    </div>
    <ProductEditor
      v-if="item.data.value"
      :key="scope"
      :item="item.data.value"
      :content="contentValues"
      :disabled="blocked"
      :content-disabled="!schema.data.value?.schema.schema_version"
      :errors="errors"
      :dirty="dirty"
      :resets="resets"
      :pending="pending"
      :uploading="uploading"
      :save-status="saveStatus"
      :error="error"
      :active-tab="pageState.tab.value"
      :initial-group="pageState.initialGroup.value"
      :focus-title="ctx.route.query.focus === 'title'"
      :image-url="imageUrl"
      @content="changeContent"
      @save="save"
      @upload="upload"
      @reload="reload"
      @retry="retry"
      @focused="focused"
      @tab="pageState.selectTab"
    >
      <template v-if="item.data.value.kind === 'variable'" #variants
        ><CatalogVariantsPage
          :root-id="id"
          :parent-stock="item.data.value.stock"
          :prepare-edit="flush"
      /></template>
    </ProductEditor>
  </div>
</template>
