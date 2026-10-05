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
import { catalogApi } from "../api/catalog.api";
import {
  catalogError,
  contentPayload,
  isUuid,
  validName,
} from "../model/forms";
import {
  productKey,
  useCatalogTenant,
  useLocales,
  useProduct,
} from "../model/queries";
import { useUnsavedChanges } from "../model/use-unsaved-changes";
import ContentFields from "../ui/ContentFields.vue";
import LocaleSelect from "../ui/LocaleSelect.vue";
import RequestError from "../ui/RequestError.vue";
const route = useRoute();
const router = useRouter();
const client = useQueryClient();
const tenant = useCatalogTenant();
const id = computed(() => String(route.params.productId ?? ""));
const locale = computed(() =>
  typeof route.query.locale === "string" ? route.query.locale : "",
);
const locales = useLocales();
const product = useProduct(id, locale);
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
            values.find((item) => item.code === "uk")?.code ?? values[0]!.code,
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
const name = ref("");
const description = ref("");
const baseline = ref("");
const loadedKey = ref("");
const validation = ref("");
const draft = computed(() => JSON.stringify([name.value, description.value]));
const identity = computed(() =>
  JSON.stringify([tenant.value, id.value, locale.value]),
);
const dirty = computed(
  () => loadedKey.value === identity.value && draft.value !== baseline.value,
);
watch(
  () => product.data.value,
  (value) => {
    if (
      !value ||
      dirty.value ||
      value.id !== id.value ||
      value.requested_locale !== locale.value
    )
      return;
    name.value = value.content?.name ?? "";
    description.value = value.content?.description ?? "";
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
    payload: ReturnType<typeof contentPayload>;
  }) => catalogApi.putProductContent(productId, language, payload),
  retry: false,
});
const saving = ref(false);
useUnsavedChanges(dirty, saving);
watch(identity, () => {
  validation.value = "";
  mutation.reset();
});
const canEdit = computed(() =>
  languages.value.some((item) => item.code === locale.value),
);
async function save() {
  if (saving.value) return;
  validation.value = "";
  if (!validName(name.value)) {
    validation.value = "Название должно содержать 1–255 символов.";
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
      payload: contentPayload(name.value, description.value),
    });
    name.value = saved.name;
    description.value = saved.description ?? "";
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
function changeLocale(value: string) {
  if (value !== locale.value)
    void router.push({ query: { ...route.query, locale: value } });
}
const formatDate = (value: string) => new Date(value).toLocaleString("ru-RU");
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold">Карточка товара</h1>
      <Button variant="outline" as-child
        ><RouterLink to="/catalog/products">К товарам</RouterLink></Button
      >
    </header>
    <RequestError
      v-if="!isUuid(id)"
      message="Некорректный ID товара. Введите UUID на странице товаров."
    />
    <template v-else>
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
                :disabled="saving"
                @change="changeLocale" /></Field></FieldGroup></CardContent
      ></Card>
      <template
        v-if="
          product.data.value && !product.isError.value && loadedKey === identity
        "
      >
        <Card class="w-full max-w-3xl"
          ><CardHeader
            ><CardTitle>{{
              product.data.value.content?.name ?? "Товар без перевода"
            }}</CardTitle
            ><CardDescription>Данные товара</CardDescription></CardHeader
          ><CardContent
            ><dl class="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt class="text-muted-foreground">ID</dt>
                <dd class="break-all">{{ product.data.value.id }}</dd>
              </div>
              <div>
                <dt class="text-muted-foreground">Тип</dt>
                <dd>{{ product.data.value.type }}</dd>
              </div>
              <div>
                <dt class="text-muted-foreground">SKU</dt>
                <dd class="break-all">
                  {{ product.data.value.sku_code }}<br />{{
                    product.data.value.sku_id
                  }}
                </dd>
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
            </dl></CardContent
          ></Card
        >
        <Card class="w-full max-w-3xl"
          ><CardHeader
            ><CardTitle>Перевод: {{ locale }}</CardTitle
            ><CardDescription>{{
              product.data.value.content
                ? "Редактирование названия и описания."
                : "Перевод отсутствует. Добавьте название и описание для этого языка."
            }}</CardDescription></CardHeader
          ><CardContent
            ><form class="flex flex-col gap-5" @submit.prevent="save">
              <p v-if="!canEdit" class="text-sm text-muted-foreground">
                Этот язык недоступен для сохранения. Существующий перевод можно
                просмотреть.
              </p>
              <FieldGroup
                ><ContentFields
                  v-model:name="name"
                  v-model:description="description"
                  :disabled="saving || !canEdit"
                  :invalid="!!validation" /></FieldGroup
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
                  saving || !canEdit || (!dirty && !!product.data.value.content)
                "
                >{{ saving ? "Сохранение…" : "Сохранить перевод" }}</Button
              >
            </form></CardContent
          ></Card
        >
      </template>
    </template>
  </div>
</template>
