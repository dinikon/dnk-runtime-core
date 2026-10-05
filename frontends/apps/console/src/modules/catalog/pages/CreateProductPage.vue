<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
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
import { catalogError, contentPayload, validName } from "../model/forms";
import { useLocales, useSkus } from "../model/queries";
import { useUnsavedChanges } from "../model/use-unsaved-changes";
import ContentFields from "../ui/ContentFields.vue";
import LocaleSelect from "../ui/LocaleSelect.vue";
import RequestError from "../ui/RequestError.vue";
const router = useRouter();
const skus = useSkus();
const locales = useLocales();
const items = computed(() => [
  ...new Map(
    (skus.data.value?.pages.flat() ?? []).map((item) => [item.id, item]),
  ).values(),
]);
const languages = computed(() =>
  [...(locales.data.value ?? [])].sort((a, b) => a.code.localeCompare(b.code)),
);
const sku = ref("");
const locale = ref("");
const name = ref("");
const description = ref("");
const withContent = ref(false);
const validation = ref("");
const succeeded = ref(false);
watch(
  languages,
  (values) => {
    if (!locale.value)
      locale.value =
        values.find((item) => item.code === "uk")?.code ??
        values[0]?.code ??
        "";
  },
  { immediate: true },
);
const mutation = useMutation({
  mutationFn: catalogApi.createProduct,
  retry: false,
});
const dirty = computed(
  () =>
    !succeeded.value &&
    !!(sku.value || withContent.value || name.value || description.value),
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
    withContent.value &&
    (!validName(name.value) ||
      !languages.value.some((item) => item.code === locale.value))
  ) {
    validation.value =
      "Выберите язык и укажите название длиной 1–255 символов.";
    return;
  }
  try {
    const product = await mutation.mutateAsync({
      sku_id: sku.value,
      contents: withContent.value
        ? [
            {
              locale: locale.value,
              ...contentPayload(name.value, description.value),
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
          <Skeleton
            v-if="skus.isPending.value"
            class="h-12"
            aria-label="Загрузка SKU"
          />
          <RequestError
            v-if="skus.isError.value"
            :message="catalogError(skus.error.value)"
            retry
            :pending="skus.isFetching.value"
            @retry="skus.refetch()"
          />
          <FieldGroup>
            <Field
              ><FieldLabel for="product-sku">SKU</FieldLabel
              ><Select
                v-model="sku"
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
              ><ContentFields
                v-model:name="name"
                v-model:description="description"
                :disabled="mutation.isPending.value"
                :invalid="!!validation && !validName(name)"
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
