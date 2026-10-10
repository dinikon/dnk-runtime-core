<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
import { catalogApi } from "../../api/catalog.api";
import { productFromDto, typeFromDto } from "../../api/catalog.mapper";
import { loadTypes } from "../../model/catalog-options";
import { useCatalogContext } from "../../model/use-catalog-context";
import CatalogHeader from "../CatalogHeader.vue";
import CatalogToolbar from "../CatalogToolbar.vue";
import ContentForm from "../forms/ContentForm.vue";
import VariantPropertiesForm from "../forms/VariantPropertiesForm.vue";
import ProductTypeSelectionForm from "../forms/ProductTypeSelectionForm.vue";
const dirty = ref<Record<string, boolean>>({}),
  pending = ref(false),
  error = ref(""),
  conflict = ref(false),
  resets = ref({ PRODUCT: 0, properties: 0, type: 0 });
const ctx = useCatalogContext(
  () => Object.values(dirty.value).some(Boolean),
  () => pending.value,
  () => {
    dirty.value = {};
    error.value = "";
    pending.value = false;
    conflict.value = false;
  },
);
const id = computed(() => String(ctx.route.params.productId));
const product = useQuery({
  queryKey: computed(() => ctx.key("get-product", id.value)),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  refetchOnWindowFocus: false,
  queryFn: ({ signal }) =>
    catalogApi.getProduct(id.value, ctx.locale.value, signal),
  select: productFromDto,
});
const variant = useQuery({
  queryKey: computed(() =>
    ctx.key("get-variant", id.value, ctx.route.params.variantId),
  ),
  enabled: computed(
    () =>
      !!ctx.route.params.variantId &&
      !!ctx.locale.value &&
      !!ctx.tenantId.value,
  ),
  refetchOnWindowFocus: false,
  queryFn: ({ signal }) =>
    catalogApi.getVariant(
      id.value,
      String(ctx.route.params.variantId),
      ctx.locale.value,
      signal,
    ),
});
const types = useQuery({
  queryKey: computed(() => ctx.key("type-options")),
  enabled: computed(() => !!ctx.locale.value && !!ctx.tenantId.value),
  queryFn: ({ signal }) => loadTypes(ctx.locale.value, signal),
});
const schema = useQuery({
  queryKey: computed(() =>
    ctx.key("get-product-type", product.data.value?.typeId),
  ),
  enabled: computed(
    () => !!product.data.value && !!ctx.locale.value && !!ctx.tenantId.value,
  ),
  queryFn: ({ signal }) =>
    catalogApi.getProductType(
      product.data.value!.typeId,
      ctx.locale.value,
      signal,
    ),
  select: typeFromDto,
});
const section = computed(() => {
  const requested = String(
    ctx.route.query.section ??
      (ctx.route.params.variantId ? "properties" : "PRODUCT"),
  );
  return ["PRODUCT", "properties", "type"].includes(requested)
    ? requested
    : "PRODUCT";
});
const failure = computed(() =>
  variant.isError.value
    ? "Позиция не найдена или недоступна."
    : product.isError.value
      ? getApiErrorStatus(product.error.value) === 404
        ? "Товар не найден."
        : getApiErrorStatus(product.error.value) === 403
          ? "Нет доступа к товару."
          : "Не удалось загрузить товар."
      : schema.isError.value
        ? "Не удалось загрузить схему."
        : "",
);
watch(
  () => [ctx.locale.value, id.value, ctx.route.params.variantId],
  () => {
    dirty.value = {};
    error.value = "";
    conflict.value = false;
  },
);
watch(section, (_next, previous) => {
  dirty.value[previous] = false;
});
async function act(
  section: "PRODUCT" | "properties" | "type",
  fn: () => Promise<unknown>,
) {
  const current = ctx.captureSession();
  if (pending.value || conflict.value) return;
  pending.value = true;
  error.value = "";
  try {
    await fn();
    if (!current()) return;
    await product.refetch();
    if (!current()) return;
    await schema.refetch();
    if (!current()) return;
    resets.value[section]++;
    dirty.value[section] = false;
  } catch (e) {
    if (!current()) return;
    conflict.value =
      getApiErrorStatus(e) === 409 ||
      getApiErrorStatus(e) === null ||
      (getApiErrorStatus(e) ?? 0) >= 500;
    error.value = getApiErrorMessage(
      e,
      "Сохранение не подтверждено. Загрузите состояние перед повторной записью.",
    );
  } finally {
    if (current()) pending.value = false;
  }
}
function content(values: Record<string, string>) {
  const p = product.data.value,
    s = schema.data.value;
  if (!p || !s) return;
  const body = {
    expected_revision: p.revision,
    expected_schema_version: s.schemaVersion,
    values,
  };
  void act("PRODUCT", () =>
    catalogApi.putProductContent(p.id, ctx.locale.value, body),
  );
}
function removeContent() {
  const p = product.data.value;
  if (!p || !window.confirm("Удалить перевод выбранной locale?")) return;
  void act("PRODUCT", () =>
    catalogApi.deleteProductContent(p.id, ctx.locale.value, p.revision),
  );
}
function properties(virtual: boolean) {
  const p = product.data.value;
  if (p)
    void act("properties", () =>
      catalogApi.setVariantProperties(p.id, p.variantId, {
        expected_revision: p.revision,
        virtual,
        downloadable: false,
      }),
    );
}
function changeType(typeId: string) {
  const p = product.data.value;
  if (p)
    void act("type", () =>
      catalogApi.changeProductType(p.id, {
        expected_revision: p.revision,
        product_type_id: typeId,
      }),
    );
}
async function reload() {
  const current = ctx.captureSession();
  if (
    Object.values(dirty.value).some(Boolean) &&
    !window.confirm(
      "Загрузить актуальное состояние и отменить локальные изменения?",
    )
  )
    return;
  const result = await product.refetch();
  if (!current()) return;
  if (result.isError) return;
  await schema.refetch();
  if (!current()) return;
  dirty.value = {};
  conflict.value = false;
  error.value = "";
  for (const key of Object.keys(resets.value) as (keyof typeof resets.value)[])
    resets.value[key]++;
}
async function remove() {
  const current = ctx.captureSession();
  const p = product.data.value;
  if (
    !p ||
    pending.value ||
    !window.confirm("Удалить товар и его единственную позицию?")
  )
    return;
  pending.value = true;
  try {
    await catalogApi.deleteProduct(p.id, p.revision);
    if (!current()) return;
    dirty.value = {};
    pending.value = false;
    await ctx.router.push({
      path: "/catalog/products",
      query: { locale: ctx.locale.value },
    });
    if (!current()) return;
  } catch (e) {
    if (!current()) return;
    error.value = getApiErrorMessage(e, "Удаление не подтверждено.");
  } finally {
    if (current()) pending.value = false;
  }
}
</script>
<template>
  <div class="max-w-4xl space-y-6 p-6">
    <CatalogHeader
      title="SIMPLE-товар"
      :description="
        product.data.value
          ? `ID ${product.data.value.id} · Ревизия ${product.data.value.revision}`
          : 'Карточка товара'
      "
    /><CatalogToolbar
      :locale="ctx.locale.value"
      :options="ctx.options.value"
      @locale="ctx.selectLocale"
    />
    <div
      v-if="error || failure"
      role="alert"
      class="rounded-lg border border-destructive p-4"
    >
      <p>{{ error || failure }}</p>
      <p v-if="conflict" class="mt-2 text-sm">
        Ввод сохранён. Для продолжения явно загрузите актуальное состояние.
      </p>
      <Button class="mt-3" variant="outline" :disabled="pending" @click="reload"
        >Загрузить актуальное состояние</Button
      >
    </div>
    <p v-if="ctx.locale.value && product.isPending.value">Загрузка…</p>
    <template v-if="product.data.value && schema.data.value && !failure"
      ><nav class="flex flex-wrap gap-2">
        <Button
          v-for="tab in [
            { id: 'PRODUCT', label: 'Контент товара' },
            { id: 'properties', label: 'Свойства позиции' },
            { id: 'type', label: 'Тип контента' },
          ]"
          :key="tab.id"
          :variant="section === tab.id ? 'default' : 'outline'"
          @click="
            ctx.router.replace({
              query: { ...ctx.route.query, section: tab.id },
            })
          "
          >{{ tab.label }}</Button
        >
      </nav>
      <ContentForm
        v-if="section === 'PRODUCT'"
        :key="id + section + ctx.locale.value + ctx.sessionKey.value"
        :blocks="schema.data.value.blocks.filter((b) => b.scope === 'PRODUCT')"
        :content="product.data.value.content"
        :pending="pending"
        :disabled="!ctx.active.value || conflict"
        :reset="resets.PRODUCT"
        @dirty="dirty.PRODUCT = $event"
        @submit="content"
        @delete="removeContent"
      /><VariantPropertiesForm
        v-if="section === 'properties'"
        :key="id + ctx.sessionKey.value"
        :virtual="product.data.value.virtual"
        :pending="pending || conflict"
        :reset="resets.properties"
        @dirty="dirty.properties = $event"
        @submit="properties"
      /><ProductTypeSelectionForm
        v-if="section === 'type'"
        :key="id + ctx.sessionKey.value"
        :type-id="product.data.value.typeId"
        :types="types.data.value ?? []"
        :pending="pending || conflict"
        :reset="resets.type"
        @dirty="dirty.type = $event"
        @submit="changeType"
      />
      <p v-if="!ctx.active.value" class="text-sm text-muted-foreground">
        Locale неактивна: существующий перевод доступен для чтения, запись
        отключена.
      </p>
      <div class="border-t pt-4">
        <Button variant="ghost" :disabled="pending" @click="remove"
          >Удалить товар</Button
        >
      </div></template
    >
  </div>
</template>
