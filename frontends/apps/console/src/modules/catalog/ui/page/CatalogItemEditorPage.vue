<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { getApiErrorMessage } from "@/app/providers/http";
import { useProductPage } from "../../model/use-product-page";
import { tabGroup } from "../../model/product-editor-layout";
import type { ProductSection } from "../../model/product.types";
import ProductHeader from "../product/ProductHeader.vue";
import ProductEditor from "../product/ProductEditor.vue";
const {
  ctx,
  id,
  scope,
  item,
  attributes,
  categories,
  tags,
  schema,
  tab,
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
} = useProductPage(true);
const sections: ProductSection[] = [
  "content",
  "status",
  "sku",
  "virtual",
  "price",
  "stock",
  "measurements",
  "metadata",
  "attributes",
  "categories",
  "tags",
  "galleries",
];
const errors = computed(() =>
  Object.fromEntries(sections.map((s) => [s, fieldError(s)])),
);
const dirty = computed(() => sections.filter(isDirty));
const references = computed(() => ({
  categories: categories.isError.value
    ? ("error" as const)
    : categories.isPending.value
      ? ("loading" as const)
      : ("ready" as const),
  tags: tags.isError.value
    ? ("error" as const)
    : tags.isPending.value
      ? ("loading" as const)
      : ("ready" as const),
  attributes: attributes.isError.value
    ? ("error" as const)
    : attributes.isPending.value
      ? ("loading" as const)
      : ("ready" as const),
}));
function retryReference(kind: "categories" | "tags" | "attributes"): void {
  void { categories, tags, attributes }[kind].refetch();
}
function focused(): void {
  const query = { ...ctx.route.query };
  delete query.focus;
  void ctx.router.replace({ query });
}
</script>
<template>
  <div class="product-editor min-h-0 min-w-0 flex-1 overflow-y-auto">
    <div
      class="mx-auto flex w-full max-w-[1440px] flex-col gap-6 p-4 pb-12 md:p-8"
    >
      <ProductHeader
        :title="item.data.value?.title ?? 'Товар без названия'"
        editing
        :locale="ctx.locale.value"
        :options="ctx.options.value"
        @back="
          ctx.router.push({
            path: '/catalog/items',
            query: { locale: ctx.locale.value },
          })
        "
        @locale="ctx.selectLocale"
        @mode="
          ctx.router.push({
            path: `/catalog/items/${id}`,
            query: { locale: ctx.locale.value },
          })
        "
      />
      <Alert
        v-if="item.isError.value || schema.isError.value"
        variant="destructive"
        ><AlertTitle>{{
          item.isError.value
            ? "Не удалось открыть товар"
            : "Не удалось загрузить поля контента"
        }}</AlertTitle
        ><AlertDescription
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
        ></Alert
      >
      <Alert v-if="!ctx.active.value && !ctx.locales.isPending.value"
        ><AlertTitle>Редактирование недоступно</AlertTitle
        ><AlertDescription
          >Выберите активный язык каталога. Сохранённые значения доступны для
          просмотра.</AlertDescription
        ></Alert
      >
      <Skeleton v-if="item.isPending.value" class="h-96 w-full" />
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
        :initial-group="ctx.route.query.tab ? tabGroup[tab] : undefined"
        :focus-name="ctx.route.query.focus === 'name'"
        :categories="categories.data.value ?? []"
        :tags="tags.data.value ?? []"
        :attributes="attributes.data.value ?? []"
        :references="references"
        :image-url="imageUrl"
        @content="changeContent"
        @save="save"
        @upload="upload"
        @reload="reload"
        @retry="retry"
        @reference="retryReference"
        @focused="focused"
      />
    </div>
  </div>
</template>
