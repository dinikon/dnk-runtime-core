<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { useUnsavedChanges } from "@/shared/model/use-unsaved-changes";
import { useCategoryLocale } from "../model/use-category-locale";
import { useCatalogTenant } from "../model/queries";
import {
  useCategories,
  categoryError,
  invalidateCategories,
} from "../model/categories";
import { categoriesApi } from "../api/categories.api";
import { validName } from "../model/forms";
import CategoryParentSelect from "../ui/CategoryParentSelect.vue";
import LocaleSelect from "../ui/LocaleSelect.vue";
import RequestError from "../ui/RequestError.vue";
const route = useRoute();
const router = useRouter();
const client = useQueryClient();
const tenant = useCatalogTenant();
const { locale, locales, languages, changeLocale } = useCategoryLocale();
const categories = useCategories(locale);
const initialParent = computed(() =>
  typeof route.query.parentId === "string" ? route.query.parentId : null,
);
const parent = ref<string | null>(initialParent.value);
const name = ref("");
const validation = ref("");
const pending = ref(false);
const succeeded = ref(false);
watch(initialParent, (value) => {
  parent.value = value;
});
const dirty = computed(
  () =>
    !succeeded.value && !!(name.value || parent.value !== initialParent.value),
);
useUnsavedChanges(dirty, pending);
const mutation = useMutation({
  mutationFn: categoriesApi.create,
  retry: false,
});
const validParent = computed(
  () =>
    !parent.value ||
    categories.data.value?.some((item) => item.id === parent.value),
);
async function submit() {
  if (pending.value) return;
  validation.value = "";
  if (
    !validName(name.value) ||
    !languages.value.some((item) => item.code === locale.value) ||
    !validParent.value
  ) {
    validation.value =
      "Укажите название длиной 1–255 символов, доступный язык и родителя.";
    return;
  }
  pending.value = true;
  try {
    const created = await mutation.mutateAsync({
      parent_id: parent.value,
      translations: [{ locale: locale.value, name: name.value.trim() }],
    });
    await invalidateCategories(client, tenant.value);
    succeeded.value = true;
    pending.value = false;
    await router.push({
      name: "catalog-category",
      params: { categoryId: created.id },
      query: { locale: locale.value },
    });
  } catch {
    /* Preserve draft. */
  } finally {
    pending.value = false;
  }
}
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold">Создать категорию</h1>
      <Button variant="outline" as-child
        ><RouterLink :to="{ name: 'catalog-categories', query: { locale } }"
          >К категориям</RouterLink
        ></Button
      >
    </header>
    <Card class="w-full max-w-3xl"
      ><CardHeader
        ><CardTitle>Новая категория</CardTitle
        ><CardDescription
          >Для создания нужен хотя бы один перевод названия.</CardDescription
        ></CardHeader
      ><CardContent
        ><form class="flex flex-col gap-5" @submit.prevent="submit">
          <RequestError
            v-if="locales.isError.value"
            :message="categoryError(locales.error.value)"
            retry
            @retry="locales.refetch()"
          /><RequestError
            v-if="categories.isError.value"
            :message="categoryError(categories.error.value)"
            retry
            @retry="categories.refetch()"
          /><FieldGroup
            ><Field
              ><FieldLabel for="category-parent">Родитель</FieldLabel
              ><CategoryParentSelect
                v-model="parent"
                :items="categories.data.value ?? []"
                :disabled="
                  pending ||
                  categories.isPending.value ||
                  categories.isError.value
                "
              />
              <p v-if="!validParent" class="text-sm text-destructive">
                Выбранный родитель недоступен. Выберите другую категорию или
                «Без родителя».
              </p></Field
            ><Field
              ><FieldLabel for="product-locale">Язык</FieldLabel
              ><LocaleSelect
                :value="locale"
                :options="languages"
                :disabled="pending || !languages.length"
                @change="changeLocale" /></Field
            ><Field :data-invalid="!!validation && !validName(name)"
              ><FieldLabel for="category-name">Название</FieldLabel
              ><Input
                id="category-name"
                v-model="name"
                :disabled="pending"
                :aria-invalid="!!validation && !validName(name)"
              /><FieldDescription
                >От 1 до 255 символов после удаления пробелов по
                краям.</FieldDescription
              ></Field
            ></FieldGroup
          ><RequestError v-if="validation" :message="validation" /><RequestError
            v-if="mutation.isError.value"
            :message="categoryError(mutation.error.value, 'create')"
          /><Button
            type="submit"
            class="self-start"
            :disabled="
              pending || !languages.length || !categories.isSuccess.value
            "
            >{{ pending ? "Создание…" : "Создать категорию" }}</Button
          >
        </form></CardContent
      ></Card
    >
  </div>
</template>
