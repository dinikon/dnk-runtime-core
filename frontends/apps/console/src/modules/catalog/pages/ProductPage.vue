<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import ProductCategoriesForm from "../ui/ProductCategoriesForm.vue";
import { categoriesApi } from "../api/categories.api";
import { useCategories, categoryError } from "../model/categories";
import { catalogApi } from "../api/catalog.api";
import { catalogError, isUuid } from "../model/forms";
import {
  productKey,
  useCatalogTenant,
  useLocales,
  useProduct,
  useProductTypes,
} from "../model/queries";
import { useUnsavedChanges } from "@/shared/model/use-unsaved-changes";
import { useUserStore } from "@/app/stores/user";
import DynamicContentFields from "../ui/DynamicContentFields.vue";
import ProductVariantsPanel from "../ui/ProductVariantsPanel.vue";
import LocaleSelect from "../ui/LocaleSelect.vue";
import RequestError from "../ui/RequestError.vue";
const route = useRoute();
const router = useRouter();
const user = useUserStore();
const client = useQueryClient();
const tenant = useCatalogTenant();
const id = computed(() => String(route.params.productId ?? ""));
const locale = computed(() =>
  typeof route.query.locale === "string" ? route.query.locale : "",
);
const locales = useLocales();
const product = useProduct(id, locale);
const productTypes = useProductTypes();
const currentType = computed(() => productTypes.data.value?.find((item) => item.id === product.data.value?.product_type_id));
const categories = useCategories(locale);
const languages = computed(() =>
  [...(locales.data.value ?? [])].sort((a, b) => a.code.localeCompare(b.code)),
);
watch(
  [languages, locale],
  ([values]) => {
    if (!locale.value && values.length)
      void router.replace({
        query: {
          ...route.query,
          locale:
            values.find((item) => item.code === user.user?.interface_language)
              ?.code ?? values[0]!.code,
        },
      });
  },
  { immediate: true },
);
const options = computed(() => {
  const all = new Map(
    languages.value.map((item) => [
      item.code,
      { code: item.code, name: item.name },
    ]),
  );
  for (const code of [
    ...(product.data.value?.content_locales ?? []),
    locale.value,
  ])
    if (code && !all.has(code)) all.set(code, { code, name: code });
  return [...all.values()].sort((a, b) => a.code.localeCompare(b.code));
});
const blocks = ref<Record<string, string>>({});
const baseline = ref("");
const loadedKey = ref("");
const validation = ref("");
const draft = computed(() => JSON.stringify(blocks.value));
const identity = computed(() =>
  JSON.stringify([tenant.value, id.value, locale.value]),
);
const dirty = computed(
  () => loadedKey.value === identity.value && draft.value !== baseline.value,
);
watch(
  [() => product.data.value, identity],
  ([value]) => {
    if (
      !value ||
      dirty.value ||
      value.id !== id.value ||
      value.requested_locale !== locale.value
    )
      return;
    blocks.value = { ...(value.content?.blocks ?? {}) };
    baseline.value = draft.value;
    loadedKey.value = identity.value;
    validation.value = "";
  },
  { immediate: true },
);
const mutation = useMutation({
  mutationFn: ({
    productId,
    language,
    payload,
  }: {
    productId: string;
    language: string;
    payload: { schema_version: number; blocks: Record<string, string> };
  }) => catalogApi.putProductContent(productId, language, payload),
  retry: false,
});
const saving = ref(false);
const selectedCategories = ref<string[]>([]);
const primaryCategory = ref<string | null>(null);
const categoriesBaseline = ref("");
const categoriesLoaded = ref("");
const categoriesSaving = ref(false);
const categoriesError = ref("");
const categoriesDraft = computed(() =>
  JSON.stringify([[...selectedCategories.value].sort(), primaryCategory.value]),
);
const categoriesDirty = computed(
  () =>
    categoriesLoaded.value === identity.value &&
    categoriesDraft.value !== categoriesBaseline.value,
);
watch(
  [() => product.data.value, identity],
  ([value]) => {
    if (
      !value ||
      value.id !== id.value ||
      value.requested_locale !== locale.value ||
      categoriesDirty.value
    )
      return;
    selectedCategories.value = (value.categories ?? []).map((item) => item.id);
    primaryCategory.value = value.primary_category_id ?? null;
    categoriesBaseline.value = categoriesDraft.value;
    categoriesLoaded.value = identity.value;
  },
  { immediate: true },
);
const anyDirty = computed(() => dirty.value || categoriesDirty.value);
const anySaving = computed(() => saving.value || categoriesSaving.value);
useUnsavedChanges(anyDirty, anySaving);
async function saveCategories() {
  if (anySaving.value || categoriesLoaded.value !== identity.value) return;
  categoriesError.value = "";
  if (
    selectedCategories.value.length &&
    (!primaryCategory.value ||
      !selectedCategories.value.includes(primaryCategory.value))
  ) {
    categoriesError.value =
      "Выберите основную категорию из назначенных товару.";
    return;
  }
  categoriesSaving.value = true;
  try {
    const saved = await categoriesApi.putProductCategories(id.value, {
      category_ids: [...new Set(selectedCategories.value)],
      primary_category_id: selectedCategories.value.length
        ? primaryCategory.value
        : null,
    });
    selectedCategories.value = saved.category_ids;
    primaryCategory.value = saved.primary_category_id;
    categoriesBaseline.value = categoriesDraft.value;
    await client.invalidateQueries({
      queryKey: productKey(tenant.value, id.value),
    });
    toast.success("Категории сохранены");
  } catch (error) {
    categoriesError.value = categoryError(error, "assign");
  } finally {
    categoriesSaving.value = false;
  }
}
watch(identity, () => {
  categoriesError.value = "";
  validation.value = "";
  mutation.reset();
});
const canEdit = computed(() =>
  languages.value.some((item) => item.code === locale.value),
);
async function save() {
  if (anySaving.value) return;
  validation.value = "";
  if (currentType.value?.blocks.some((item) => item.scope === "product" && item.required && !blocks.value[item.code]?.trim())) {
    validation.value = "Заполните обязательные блоки.";
    return;
  }
  if (!canEdit.value || loadedKey.value !== identity.value) return;
  const productId = id.value;
  const language = locale.value;
  const tenantId = tenant.value;
  saving.value = true;
  try {
    const saved = await mutation.mutateAsync({
      productId,
      language,
      payload: { schema_version: product.data.value!.schema_version, blocks: Object.fromEntries(Object.entries(blocks.value).filter(([, value]) => value.trim())) },
    });
    blocks.value = { ...saved.blocks };
    baseline.value = draft.value;
    await client.invalidateQueries({
      queryKey: productKey(tenantId, productId),
    });
    toast.success("Перевод сохранён");
  } catch {
    /* Keep draft and show mutation error. */
  } finally {
    saving.value = false;
  }
}
async function deleteTranslation() {
  if (!product.data.value?.content || !window.confirm("Удалить перевод этого языка?")) return;
  try {
    await catalogApi.deleteProductContent(id.value, locale.value);
    blocks.value = {};
    baseline.value = draft.value;
    await client.invalidateQueries({ queryKey: productKey(tenant.value, id.value) });
    toast.success("Перевод удалён");
  } catch (error) {
    validation.value = catalogError(error);
  }
}
const typeSelection = ref("");
watch(currentType, (value) => { if (value) typeSelection.value = value.id; }, { immediate: true });
async function changeType() {
  const target = productTypes.data.value?.find((item) => item.id === typeSelection.value);
  if (!target || !product.data.value || target.id === product.data.value.product_type_id) return;
  try {
    await catalogApi.putProductType(id.value, target.id, target.schema_version);
    await client.invalidateQueries({ queryKey: productKey(tenant.value, id.value) });
    toast.success("Тип товара изменён");
  } catch (error) { validation.value = catalogError(error); }
}
function changeLocale(value: string) {
  if (value !== locale.value)
    void router.push({ query: { ...route.query, locale: value } });
}
const formatDate = (value: string) => new Date(value).toLocaleString("ru-RU");
const deleting = ref(false);
const deleteError = ref("");
const activeTab = ref<"overview" | "variants" | "translations">("overview");
async function removeProduct() {
  if (
    deleting.value ||
    !window.confirm(
      "Удалить товар, варианты и переводы? SKU в Inventory сохранятся.",
    )
  )
    return;
  deleting.value = true;
  deleteError.value = "";
  try {
    await catalogApi.deleteProduct(id.value);
    await client.invalidateQueries({
      queryKey: ["catalog", tenant.value, "products"],
    });
    toast.success("Товар удалён");
    await router.push({ name: "catalog-products" });
  } catch (error) {
    deleteError.value = catalogError(error);
  } finally {
    deleting.value = false;
  }
}
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">
          {{ product.data.value?.content?.blocks.title ?? product.data.value?.sku_code ?? product.data.value?.id ?? "Карточка товара" }}
        </h1>
        <p v-if="product.data.value" class="text-sm text-muted-foreground">
          {{
            product.data.value.kind === "simple"
              ? "Простой товар"
              : "Вариативный товар"
          }}
          · {{ product.data.value.variants.length }} вариантов
        </p>
      </div>
      <Button variant="outline" as-child
        ><RouterLink to="/catalog/products">К товарам</RouterLink></Button
      >
      <Button variant="destructive" :disabled="deleting" @click="removeProduct"
        >Удалить товар</Button
      >
    </header>
    <RequestError
      v-if="!isUuid(id)"
      message="Некорректный ID товара. Введите UUID на странице товаров."
    />
    <template v-else>
      <RequestError v-if="deleteError" :message="deleteError" />
      <Skeleton
        v-if="locales.isPending.value || (locale && product.isPending.value)"
        class="h-48"
        aria-label="Загрузка карточки"
      />
      <RequestError
        v-if="locales.isError.value"
        :message="catalogError(locales.error.value)"
        retry
        :pending="locales.isFetching.value"
        @retry="locales.refetch()"
      />
      <p
        v-if="locales.isSuccess.value && !languages.length && !locale"
        class="text-sm text-muted-foreground"
      >
        Нет доступных языков для открытия карточки.
      </p>
      <RequestError
        v-if="product.isError.value"
        :message="catalogError(product.error.value)"
        retry
        :pending="product.isFetching.value"
        @retry="product.refetch()"
      />
      <Card v-if="options.length" class="w-full max-w-3xl"
        ><CardHeader><CardTitle>Язык карточки</CardTitle></CardHeader
        ><CardContent
          ><FieldGroup
            ><Field
              ><FieldLabel for="product-locale">Язык</FieldLabel
              ><LocaleSelect
                :options="options"
                :value="locale"
                :disabled="anySaving"
                @change="changeLocale" /></Field></FieldGroup></CardContent
      ></Card>
      <template
        v-if="
          product.data.value && !product.isError.value && loadedKey === identity
        "
      >
        <nav class="flex gap-1 border-b" aria-label="Разделы товара">
          <button
            v-for="tab in [
              ['overview', 'Обзор'],
              ['variants', 'Варианты'],
              ['translations', 'Переводы'],
            ] as const"
            :key="tab[0]"
            type="button"
            class="border-b-2 px-4 py-2 text-sm"
            :class="
              activeTab === tab[0]
                ? 'border-primary font-medium'
                : 'border-transparent text-muted-foreground'
            "
            @click="activeTab = tab[0]"
          >
            {{ tab[1] }}
          </button>
        </nav>
        <Card v-if="activeTab === 'overview'" class="w-full"
          ><CardHeader
            ><CardTitle>{{
              product.data.value.content?.blocks.title ?? product.data.value.sku_code ?? product.data.value.id
            }}</CardTitle
            ><CardDescription>Данные товара</CardDescription></CardHeader
          ><CardContent
            ><dl class="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt class="text-muted-foreground">ID</dt>
                <dd class="break-all">{{ product.data.value.id }}</dd>
              </div>
              <div>
                <dt class="text-muted-foreground">Вид</dt>
                <dd>
                  {{
                    product.data.value.kind === "simple"
                      ? "Простой"
                      : "Вариативный"
                  }}
                </dd>
              </div>
              <div>
                <dt class="text-muted-foreground">Вариантов</dt>
                <dd>{{ product.data.value.variants.length }}</dd>
              </div>
              <div>
                <dt class="text-muted-foreground">Тип товара</dt>
                <dd>{{ currentType?.translations[user.user?.interface_language ?? ''] ?? currentType?.code ?? product.data.value.product_type_id }}</dd>
              </div>
              <div>
                <dt class="text-muted-foreground">Переводы</dt>
                <dd class="flex flex-wrap gap-2">
                  <Badge
                    v-for="code in product.data.value.content_locales"
                    :key="code"
                    variant="secondary"
                    >{{ code }}</Badge
                  ><span v-if="!product.data.value.content_locales.length"
                    >Нет переводов</span
                  >
                </dd>
              </div>
              <div>
                <dt class="text-muted-foreground">Создан</dt>
                <dd>{{ formatDate(product.data.value.created_at) }}</dd>
              </div>
              <div>
                <dt class="text-muted-foreground">Обновлён</dt>
                <dd>{{ formatDate(product.data.value.updated_at) }}</dd>
              </div>
            </dl><div class="mt-5 flex max-w-md gap-2"><select v-model="typeSelection" class="h-9 flex-1 rounded-md border bg-background px-3 text-sm"><option v-for="item in productTypes.data.value ?? []" :key="item.id" :value="item.id">{{ item.translations[user.user?.interface_language ?? ''] ?? item.code }}</option></select><Button variant="outline" :disabled="typeSelection === product.data.value.product_type_id" @click="changeType">Изменить тип</Button></div></CardContent
          ></Card
        >
        <ProductVariantsPanel
          v-show="activeTab === 'variants'"
          :product="product.data.value"
          :locale="locale"
          :editable="canEdit"
          :schema="currentType?.blocks ?? []"
          :label-locale="user.user?.interface_language"
        />
        <Card v-if="activeTab === 'translations'" class="w-full"
          ><CardHeader
            ><CardTitle>Перевод: {{ locale }}</CardTitle
            ><CardDescription>{{
              product.data.value.content
                ? "Редактирование блоков выбранного языка."
                : "Перевод отсутствует. Заполните блоки для этого языка."
            }}</CardDescription></CardHeader
          ><CardContent
            ><form class="flex flex-col gap-5" @submit.prevent="save">
              <p v-if="!canEdit" class="text-sm text-muted-foreground">
                Этот язык недоступен для сохранения. Существующий перевод можно
                просмотреть.
              </p>
              <FieldGroup
                ><DynamicContentFields
                  v-if="currentType"
                  v-model="blocks"
                  :blocks="currentType.blocks"
                  scope="product"
                  :label-locale="user.user?.interface_language"
                  :disabled="anySaving || !canEdit" /></FieldGroup
              ><RequestError
                v-if="validation"
                :message="validation"
              /><RequestError
                v-if="mutation.isError.value"
                :message="catalogError(mutation.error.value)"
              /><Button
                type="submit"
                class="self-start"
                :disabled="
                  anySaving ||
                  !canEdit ||
                  (!dirty && !!product.data.value.content)
                "
                >{{ saving ? "Сохранение…" : "Сохранить перевод" }}</Button
              >
              <Button v-if="product.data.value.content" type="button" variant="destructive" class="self-start" :disabled="anySaving" @click="deleteTranslation">Удалить перевод</Button>
            </form></CardContent
          ></Card
        >
        <ProductCategoriesForm
          v-if="activeTab === 'overview'"
          v-model:selected="selectedCategories"
          v-model:primary="primaryCategory"
          :items="categories.data.value ?? []"
          :locale="locale"
          :pending="anySaving"
          :loading="categories.isPending.value"
          :available="categories.isSuccess.value"
          :load-error="
            categories.isError.value
              ? categoryError(categories.error.value)
              : ''
          "
          :error="categoriesError"
          :dirty="categoriesDirty"
          @save="saveCategories"
          @retry="categories.refetch()"
        />
      </template>
    </template>
  </div>
</template>
