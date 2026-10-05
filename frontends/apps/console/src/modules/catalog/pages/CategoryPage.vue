<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQueryClient } from "@tanstack/vue-query";
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog";
import { useUnsavedChanges } from "@/shared/model/use-unsaved-changes";
import { useCategoryLocale } from "../model/use-category-locale";
import { useCatalogTenant } from "../model/queries";
import {
  useCategories,
  useCategory,
  categoryError,
  categoryLabel,
  invalidateCategories,
} from "../model/categories";
import { categoriesApi } from "../api/categories.api";
import { isUuid, validName } from "../model/forms";
import CategoryParentSelect from "../ui/CategoryParentSelect.vue";
import LocaleSelect from "../ui/LocaleSelect.vue";
import RequestError from "../ui/RequestError.vue";
const route = useRoute();
const router = useRouter();
const client = useQueryClient();
const tenant = useCatalogTenant();
const id = computed(() => String(route.params.categoryId ?? ""));
const { locale, locales, languages, changeLocale } = useCategoryLocale();
const category = useCategory(id, locale);
const categories = useCategories(locale);
const name = ref("");
const parent = ref<string | null>(null);
const nameBaseline = ref("");
const parentBaseline = ref<string | null>(null);
const loaded = ref("");
const pending = ref(false);
const removed = ref(false);
const contentError = ref("");
const moveError = ref("");
const deleteError = ref("");
const deleting = ref(false);
const identity = computed(() =>
  JSON.stringify([tenant.value, id.value, locale.value]),
);
const contentDirty = computed(
  () => loaded.value === identity.value && name.value !== nameBaseline.value,
);
const parentDirty = computed(
  () =>
    loaded.value === identity.value && parent.value !== parentBaseline.value,
);
const dirty = computed(
  () => !removed.value && (contentDirty.value || parentDirty.value),
);
useUnsavedChanges(dirty, pending);
watch(
  [() => category.data.value, identity],
  ([value]) => {
    if (
      !value ||
      value.id !== id.value ||
      value.requested_locale !== locale.value
    )
      return;
    if (!contentDirty.value) {
      name.value = value.name ?? "";
      nameBaseline.value = name.value;
    }
    if (!parentDirty.value) {
      parent.value = value.parent_id;
      parentBaseline.value = value.parent_id;
    }
    loaded.value = identity.value;
  },
  { immediate: true },
);
watch(identity, () => {
  contentError.value = "";
  moveError.value = "";
  deleteError.value = "";
});
const options = computed(() => {
  const map = new Map(
    languages.value.map((item) => [
      item.code,
      { code: item.code, name: item.name },
    ]),
  );
  for (const code of [
    ...(category.data.value?.translations.map((item) => item.locale) ?? []),
    locale.value,
  ])
    if (code && !map.has(code)) map.set(code, { code, name: code });
  return [...map.values()].sort((a, b) => a.code.localeCompare(b.code));
});
const canEdit = computed(() =>
  languages.value.some((item) => item.code === locale.value),
);
const parentName = computed(() => {
  const parentId = category.data.value?.parent_id;
  if (!parentId) return "Без родителя";
  const item = categories.data.value?.find((item) => item.id === parentId);
  return item ? categoryLabel(item) : parentId;
});
async function saveContent() {
  if (pending.value) return;
  contentError.value = "";
  if (!validName(name.value)) {
    contentError.value = "Название должно содержать 1–255 символов.";
    return;
  }
  if (!canEdit.value) return;
  pending.value = true;
  try {
    const result = await categoriesApi.putContent(
      id.value,
      locale.value,
      name.value.trim(),
    );
    name.value = result.name;
    nameBaseline.value = result.name;
    await invalidateCategories(client, tenant.value);
  } catch (error) {
    contentError.value = categoryError(error, "content");
  } finally {
    pending.value = false;
  }
}
async function move() {
  if (pending.value) return;
  moveError.value = "";
  pending.value = true;
  try {
    const result = await categoriesApi.move(id.value, parent.value);
    parent.value = result.parent_id;
    parentBaseline.value = result.parent_id;
    await invalidateCategories(client, tenant.value);
  } catch (error) {
    moveError.value = categoryError(error, "move");
  } finally {
    pending.value = false;
  }
}
async function remove() {
  if (pending.value) return;
  deleteError.value = "";
  pending.value = true;
  try {
    await categoriesApi.delete(id.value);
    removed.value = true;
    client.removeQueries({
      queryKey: ["catalog", tenant.value, "categories", "detail", id.value],
    });
    await invalidateCategories(client, tenant.value);
    deleting.value = false;
    pending.value = false;
    await router.push({
      name: "catalog-categories",
      query: { locale: locale.value },
    });
  } catch (error) {
    deleteError.value = categoryError(error, "delete");
  } finally {
    pending.value = false;
  }
}
const date = (value: string) => new Date(value).toLocaleString("ru-RU");
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold">Карточка категории</h1>
      <Button variant="outline" as-child
        ><RouterLink :to="{ name: 'catalog-categories', query: { locale } }"
          >К категориям</RouterLink
        ></Button
      >
    </header>
    <p
      v-if="locales.isSuccess.value && !languages.length && !locale"
      class="text-sm text-muted-foreground"
    >
      Нет доступных языков для открытия категории.
    </p>
    <RequestError
      v-if="!isUuid(id)"
      message="Некорректный ID категории."
    /><RequestError
      v-if="locales.isError.value"
      :message="categoryError(locales.error.value)"
      retry
      @retry="locales.refetch()"
    /><Skeleton
      v-if="locales.isPending.value || (locale && category.isPending.value)"
      class="h-48"
      aria-label="Загрузка категории"
    /><RequestError
      v-if="category.isError.value"
      :message="categoryError(category.error.value)"
      retry
      :pending="category.isFetching.value"
      @retry="category.refetch()"
    /><Card v-if="options.length" class="w-full max-w-3xl"
      ><CardHeader><CardTitle>Язык категории</CardTitle></CardHeader
      ><CardContent
        ><FieldGroup
          ><Field
            ><FieldLabel for="product-locale">Язык</FieldLabel
            ><LocaleSelect
              :value="locale"
              :options="options"
              :disabled="pending"
              @change="changeLocale" /></Field></FieldGroup></CardContent></Card
    ><template
      v-if="
        category.data.value && !category.isError.value && loaded === identity
      "
      ><Card class="w-full max-w-3xl"
        ><CardHeader
          ><CardTitle class="break-words">{{
            categoryLabel(category.data.value)
          }}</CardTitle
          ><CardDescription>Данные категории</CardDescription></CardHeader
        ><CardContent class="flex flex-col gap-5"
          ><dl class="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt class="text-muted-foreground">ID</dt>
              <dd class="break-all">{{ id }}</dd>
            </div>
            <div>
              <dt class="text-muted-foreground">Родитель</dt>
              <dd class="break-words">{{ parentName }}</dd>
            </div>
            <div>
              <dt class="text-muted-foreground">Создана</dt>
              <dd>{{ date(category.data.value.created_at) }}</dd>
            </div>
            <div>
              <dt class="text-muted-foreground">Обновлена</dt>
              <dd>{{ date(category.data.value.updated_at) }}</dd>
            </div>
            <div>
              <dt class="text-muted-foreground">Создал</dt>
              <dd class="break-all">{{ category.data.value.created_by }}</dd>
            </div>
            <div>
              <dt class="text-muted-foreground">Обновил</dt>
              <dd class="break-all">{{ category.data.value.updated_by }}</dd>
            </div>
            <div>
              <dt class="text-muted-foreground">Переводы</dt>
              <dd>
                {{
                  category.data.value.translations
                    .map((item) => item.locale)
                    .join(", ")
                }}
              </dd>
            </div>
          </dl>
          <div class="flex flex-wrap gap-3">
            <Button variant="outline" as-child
              ><RouterLink
                :to="{
                  name: 'catalog-category-new',
                  query: { locale, parentId: id },
                }"
                >Создать подкатегорию</RouterLink
              ></Button
            ><Button
              variant="destructive"
              :disabled="pending"
              @click="deleting = true"
              >Удалить</Button
            >
          </div></CardContent
        ></Card
      ><Card class="w-full max-w-3xl"
        ><CardHeader
          ><CardTitle>Перевод: {{ locale }}</CardTitle
          ><CardDescription>{{
            category.data.value.name === null
              ? "Перевод отсутствует. Добавьте название для этого языка."
              : "Редактирование названия категории."
          }}</CardDescription></CardHeader
        ><CardContent
          ><form class="flex flex-col gap-5" @submit.prevent="saveContent">
            <p v-if="!canEdit" class="text-sm text-muted-foreground">
              Этот язык недоступен для сохранения.
            </p>
            <FieldGroup
              ><Field :data-invalid="!!contentError && !validName(name)"
                ><FieldLabel for="category-name">Название</FieldLabel
                ><Input
                  id="category-name"
                  v-model="name"
                  :disabled="pending || !canEdit"
                  :aria-invalid="!!contentError && !validName(name)"
                /><FieldDescription
                  >От 1 до 255 символов.</FieldDescription
                ></Field
              ></FieldGroup
            ><RequestError v-if="contentError" :message="contentError" /><Button
              type="submit"
              class="self-start"
              :disabled="
                pending ||
                !canEdit ||
                (!contentDirty && category.data.value.name !== null)
              "
              >Сохранить перевод</Button
            >
          </form></CardContent
        ></Card
      ><Card class="w-full max-w-3xl"
        ><CardHeader
          ><CardTitle>Переместить категорию</CardTitle
          ><CardDescription
            >Выберите нового родителя или перенесите категорию в
            корень.</CardDescription
          ></CardHeader
        ><CardContent
          ><form class="flex flex-col gap-5" @submit.prevent="move">
            <RequestError
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
                  :exclude-id="id"
                  :disabled="
                    pending || !categories.isSuccess.value
                  " /></Field></FieldGroup
            ><RequestError v-if="moveError" :message="moveError" /><Button
              type="submit"
              class="self-start"
              :disabled="pending || !parentDirty || !categories.isSuccess.value"
              >Сохранить родителя</Button
            >
          </form></CardContent
        ></Card
      ></template
    ><AlertDialog
      :open="deleting"
      @update:open="
        (value) => {
          if (!pending) deleting = value;
        }
      "
      ><AlertDialogContent
        ><AlertDialogHeader
          ><AlertDialogTitle>Удалить категорию?</AlertDialogTitle
          ><AlertDialogDescription class="break-all"
            >{{
              category.data.value ? categoryLabel(category.data.value) : id
            }}
            · {{ id }}. Удаление возможно, если нет подкатегорий и связанных
            товаров.</AlertDialogDescription
          ></AlertDialogHeader
        ><RequestError
          v-if="deleteError"
          :message="deleteError"
        /><AlertDialogFooter
          ><AlertDialogCancel :disabled="pending">Отмена</AlertDialogCancel
          ><Button variant="destructive" :disabled="pending" @click="remove">{{
            pending ? "Удаление…" : "Удалить категорию"
          }}</Button></AlertDialogFooter
        ></AlertDialogContent
      ></AlertDialog
    >
  </div>
</template>
