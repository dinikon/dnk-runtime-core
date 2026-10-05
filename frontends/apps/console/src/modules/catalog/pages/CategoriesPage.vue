<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { useCategoryLocale } from "../model/use-category-locale";
import { useCategories, categoryError } from "../model/categories";
import CategoryTree from "../ui/CategoryTree.vue";
import LocaleSelect from "../ui/LocaleSelect.vue";
import RequestError from "../ui/RequestError.vue";
const { locale, locales, languages, changeLocale } = useCategoryLocale();
const categories = useCategories(locale);
const options = computed(() =>
  languages.value.some((item) => item.code === locale.value) || !locale.value
    ? languages.value
    : [...languages.value, { code: locale.value, name: locale.value }],
);
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold">Категории</h1>
      <Button as-child
        ><RouterLink
          :to="{
            name: 'catalog-category-new',
            query: locale ? { locale } : {},
          }"
          >Создать категорию</RouterLink
        ></Button
      >
    </header>
    <Card
      ><CardHeader
        ><CardTitle>Категории товаров</CardTitle
        ><CardDescription
          >Выберите язык и откройте категорию для управления переводами и
          родителем.</CardDescription
        ></CardHeader
      ><CardContent class="flex flex-col gap-5"
        ><RequestError
          v-if="locales.isError.value"
          :message="categoryError(locales.error.value)"
          retry
          @retry="locales.refetch()"
        /><FieldGroup
          ><Field
            ><FieldLabel for="product-locale">Язык</FieldLabel
            ><LocaleSelect
              :options="options"
              :value="locale"
              :disabled="!options.length"
              @change="changeLocale" /></Field></FieldGroup
        ><Skeleton
          v-if="
            locales.isPending.value || (locale && categories.isPending.value)
          "
          class="h-48"
          aria-label="Загрузка категорий"
        /><RequestError
          v-if="categories.isError.value"
          :message="categoryError(categories.error.value)"
          retry
          :pending="categories.isFetching.value"
          @retry="categories.refetch()"
        /><CategoryTree
          v-else-if="categories.data.value?.length"
          :items="categories.data.value"
          :locale="locale"
        />
        <Empty v-else-if="categories.isSuccess.value"
          ><EmptyHeader
            ><EmptyTitle>Категорий пока нет</EmptyTitle
            ><EmptyDescription
              >Создайте первую категорию.</EmptyDescription
            ></EmptyHeader
          ></Empty
        >
        <p
          v-if="locales.isSuccess.value && !languages.length && !locale"
          class="text-sm text-muted-foreground"
        >
          Нет доступных языков.
        </p></CardContent
      ></Card
    >
  </div>
</template>
