<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useMutation } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { catalogApi } from "../api/catalog.api";
import { catalogError } from "../model/forms";
import { useLocales, useProductTypes } from "../model/queries";
import { useSkus, useSku, inventoryError } from "@/modules/inventory";
import { useUnsavedChanges } from "@/shared/model/use-unsaved-changes";
import { useUserStore } from "@/app/stores/user";
import DynamicContentFields from "../ui/DynamicContentFields.vue";
import LocaleSelect from "../ui/LocaleSelect.vue";
import RequestError from "../ui/RequestError.vue";
const router = useRouter();
const user = useUserStore();
const route = useRoute();
const requestedSkuId = computed(() =>
  typeof route.query.skuId === "string" ? route.query.skuId : "",
);
const selectedSku = useSku(requestedSkuId);
const ignoredPrefill = ref(false);
const skus = useSkus();
const locales = useLocales();
const productTypes = useProductTypes();
const items = computed(() => [
  ...new Map(
    [
      ...(skus.data.value?.pages.flat() ?? []),
      ...(selectedSku.data.value ? [selectedSku.data.value] : []),
    ].map((item) => [item.id, item]),
  ).values(),
]);
const languages = computed(() =>
  [...(locales.data.value ?? [])].sort((a, b) => a.code.localeCompare(b.code)),
);
const sku = ref("");
const kind = ref<"simple" | "variable">("simple");
const extraSkuIds = ref<string[]>([""]);
watch(requestedSkuId, () => {
  ignoredPrefill.value = false;
  sku.value = "";
});
watch(
  () => selectedSku.data.value,
  (item) => {
    if (
      item &&
      item.id === requestedSkuId.value &&
      !ignoredPrefill.value &&
      !sku.value
    )
      sku.value = item.id;
  },
  { immediate: true },
);
function chooseSku(value: unknown) {
  if (!value) return;
  ignoredPrefill.value = true;
  sku.value = String(value);
}
const locale = ref("");
const productTypeId = ref("");
const blockValues = ref<Record<string, string>>({});
const selectedType = computed(() => productTypes.data.value?.find((item) => item.id === productTypeId.value));
watch(() => productTypes.data.value, (values) => {
  if (!productTypeId.value && values?.length) productTypeId.value = values.find((item) => item.code === "clean")?.id ?? values[0]!.id;
});
const withContent = ref(false);
const validation = ref("");
const succeeded = ref(false);
watch(
  languages,
  (values) => {
    if (!locale.value)
      locale.value =
        values.find((item) => item.code === user.user?.interface_language)
          ?.code ??
        values[0]?.code ??
        "";
  },
  { immediate: true },
);
const mutation = useMutation({
  mutationFn: async (payload: {
    sku_id: string;
    product_type_id: string;
    schema_version: number;
    contents: { locale: string; blocks: Record<string, string> }[];
  }) =>
    kind.value === "simple"
      ? catalogApi.createProduct(payload)
      : catalogApi.createVariableProduct({
          sku_ids: [payload.sku_id, ...extraSkuIds.value],
          contents: payload.contents,
          product_type_id: payload.product_type_id,
          schema_version: payload.schema_version,
        }),
  retry: false,
});
const dirty = computed(
  () =>
    !succeeded.value &&
    !!(
      sku.value ||
      kind.value === "variable" ||
      extraSkuIds.value.some(Boolean) ||
      withContent.value ||
      Object.values(blockValues.value).some(Boolean)
    ),
);
useUnsavedChanges(dirty, mutation.isPending);
async function submit() {
  if (mutation.isPending.value) return;
  validation.value = "";
  if (!sku.value) {
    validation.value = "Выберите SKU.";
    return;
  }
  if (
    kind.value === "variable" &&
    (!extraSkuIds.value.length ||
      extraSkuIds.value.some((value) => !value) ||
      new Set([sku.value, ...extraSkuIds.value]).size !==
        extraSkuIds.value.length + 1)
  ) {
    validation.value =
      "Для вариативного товара выберите минимум два разных SKU.";
    return;
  }
  if (!selectedType.value) {
    validation.value = "Выберите тип товара.";
    return;
  }
  if (withContent.value && (!languages.value.some((item) => item.code === locale.value) || selectedType.value.blocks.some((item) => item.scope === "product" && item.required && !blockValues.value[item.code]?.trim()))) {
    validation.value = "Выберите язык и заполните обязательные блоки.";
    return;
  }
  try {
    const product = await mutation.mutateAsync({
      sku_id: sku.value,
      product_type_id: selectedType.value.id,
      schema_version: selectedType.value.schema_version,
      contents: withContent.value
        ? [
            {
              locale: locale.value,
              blocks: Object.fromEntries(Object.entries(blockValues.value).filter(([, value]) => value.trim())),
            },
          ]
        : [],
    });
    succeeded.value = true;
    await router.push({
      name: "catalog-product",
      params: { productId: product.id },
      query: locale.value ? { locale: locale.value } : {},
    });
  } catch {
    /* Mutation state renders the error without clearing the form. */
  }
}
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold">Создать товар</h1>
      <Button variant="outline" as-child
        ><RouterLink to="/catalog/products">К товарам</RouterLink></Button
      >
    </header>
    <Card class="w-full max-w-2xl"
      ><CardHeader
        ><CardTitle>Новая карточка</CardTitle
        ><CardDescription
          >Выберите существующий SKU. Первый перевод можно добавить сейчас или
          позже.</CardDescription
        ></CardHeader
      ><CardContent>
        <form class="flex flex-col gap-5" @submit.prevent="submit">
          <div class="flex gap-2">
            <Button
              type="button"
              :variant="kind === 'simple' ? 'default' : 'outline'"
              @click="kind = 'simple'"
              >Простой</Button
            ><Button
              type="button"
              :variant="kind === 'variable' ? 'default' : 'outline'"
              @click="kind = 'variable'"
              >Вариативный</Button
            >
          </div>
          <Skeleton
            v-if="skus.isPending.value"
            class="h-12"
            aria-label="Загрузка SKU"
          />
          <RequestError
            v-if="skus.isError.value"
            :message="inventoryError(skus.error.value)"
            retry
            :pending="skus.isFetching.value"
            @retry="skus.refetch()"
          />
          <Skeleton
            v-if="
              requestedSkuId && selectedSku.isPending.value && !ignoredPrefill
            "
            class="h-12"
            aria-label="Загрузка выбранного SKU"
          />
          <RequestError
            v-if="
              requestedSkuId && selectedSku.isError.value && !ignoredPrefill
            "
            :message="inventoryError(selectedSku.error.value)"
            retry
            :pending="selectedSku.isFetching.value"
            @retry="selectedSku.refetch()"
          />
          <FieldGroup>
            <Field><FieldLabel for="product-type">Тип товара</FieldLabel>
              <Select :model-value="productTypeId" @update:model-value="productTypeId = String($event ?? '')">
                <SelectTrigger id="product-type" class="w-full"><SelectValue placeholder="Выберите тип" /></SelectTrigger>
                <SelectContent><SelectGroup><SelectItem v-for="item in productTypes.data.value ?? []" :key="item.id" :value="item.id">{{ item.translations[user.user?.interface_language ?? ''] ?? item.translations.ru ?? item.code }}</SelectItem></SelectGroup></SelectContent>
              </Select>
            </Field>
            <Field
              ><FieldLabel for="product-sku">SKU</FieldLabel
              ><Select
                :model-value="sku"
                @update:model-value="chooseSku"
                :disabled="mutation.isPending.value || !items.length"
                ><SelectTrigger id="product-sku" class="w-full"
                  ><SelectValue placeholder="Выберите SKU" /></SelectTrigger
                ><SelectContent
                  ><SelectGroup
                    ><SelectItem
                      v-for="item in items"
                      :key="item.id"
                      :value="item.id"
                      >{{ item.code }} — {{ item.title }}</SelectItem
                    ></SelectGroup
                  ></SelectContent
                ></Select
              >
              <p
                v-if="
                  !skus.isPending.value && !skus.isError.value && !items.length
                "
                class="text-sm text-muted-foreground"
              >
                SKU пока нет. Для создания товара нужен существующий SKU.
              </p></Field
            >
          </FieldGroup>
          <template v-if="kind === 'variable'">
            <Field v-for="(value, index) in extraSkuIds" :key="index">
              <FieldLabel>SKU варианта {{ index + 2 }}</FieldLabel>
              <div class="flex gap-2">
                <Select
                  :model-value="value"
                  @update:model-value="
                    extraSkuIds[index] = String($event ?? '')
                  "
                  ><SelectTrigger class="w-full"
                    ><SelectValue placeholder="Выберите SKU" /></SelectTrigger
                  ><SelectContent
                    ><SelectGroup
                      ><SelectItem
                        v-for="item in items"
                        :key="item.id"
                        :value="item.id"
                        >{{ item.code }} — {{ item.title }}</SelectItem
                      ></SelectGroup
                    ></SelectContent
                  ></Select
                ><Button
                  type="button"
                  variant="outline"
                  :disabled="extraSkuIds.length === 1"
                  @click="extraSkuIds.splice(index, 1)"
                  >Удалить</Button
                >
              </div>
            </Field>
            <Button
              type="button"
              variant="outline"
              class="self-start"
              @click="extraSkuIds.push('')"
              >Добавить вариант</Button
            >
          </template>
          <Button
            v-if="skus.hasNextPage.value"
            type="button"
            variant="outline"
            class="self-start"
            :disabled="skus.isFetching.value || mutation.isPending.value"
            @click="skus.fetchNextPage()"
            >{{
              skus.isFetchingNextPage.value ? "Загрузка…" : "Загрузить ещё"
            }}</Button
          >
          <label class="flex items-center gap-2 text-sm"
            ><input
              v-model="withContent"
              type="checkbox"
              :disabled="mutation.isPending.value"
            />Добавить первый перевод</label
          >
          <template v-if="withContent">
            <Skeleton
              v-if="locales.isPending.value"
              class="h-12"
              aria-label="Загрузка языков"
            />
            <RequestError
              v-if="locales.isError.value"
              :message="catalogError(locales.error.value)"
              retry
              :pending="locales.isFetching.value"
              @retry="locales.refetch()"
            />
            <p
              v-if="locales.isSuccess.value && !languages.length"
              class="text-sm text-muted-foreground"
            >
              Нет доступных языков. Товар можно создать без перевода.
            </p>
            <FieldGroup
              ><Field
                ><FieldLabel for="product-locale">Язык</FieldLabel
                ><LocaleSelect
                  :options="languages"
                  :value="locale"
                  :disabled="mutation.isPending.value || !languages.length"
                  @change="locale = $event" /></Field
              ><DynamicContentFields
                v-if="selectedType"
                v-model="blockValues"
                :blocks="selectedType.blocks"
                scope="product"
                :label-locale="user.user?.interface_language"
                :disabled="mutation.isPending.value"
            /></FieldGroup>
          </template>
          <RequestError v-if="validation" :message="validation" />
          <RequestError
            v-if="mutation.isError.value"
            :message="catalogError(mutation.error.value)"
          />
          <Button
            type="submit"
            class="self-start"
            :disabled="
              mutation.isPending.value ||
              !items.length ||
              (withContent && !languages.length)
            "
            >{{
              mutation.isPending.value ? "Создание…" : "Создать товар"
            }}</Button
          >
        </form>
      </CardContent></Card
    >
  </div>
</template>
