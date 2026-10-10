<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
import { catalogApi } from "../../api/catalog.api";
import { loadCategories } from "../../model/catalog-options";
import { useCatalogContext } from "../../model/use-catalog-context";
import CatalogHeader from "../CatalogHeader.vue";
import CatalogToolbar from "../CatalogToolbar.vue";
import ClassificationLabelForm from "../forms/ClassificationLabelForm.vue";
import CategoryParentForm from "../forms/CategoryParentForm.vue";
const props = defineProps<{ category: boolean }>();
const dirty = ref<Record<string, boolean>>({}),
  pending = ref(false),
  error = ref(""),
  conflict = ref(false),
  resets = ref({ label: 0, parent: 0 });
const cache = useQueryClient();
const ctx = useCatalogContext(
  () => Object.values(dirty.value).some(Boolean),
  () => pending.value,
  () => {
    dirty.value = {};
    pending.value = false;
    error.value = "";
    conflict.value = false;
  },
);
const id = computed(() => String(ctx.route.params.classificationId ?? ""));
const collection = computed(() => (props.category ? "categories" : "tags"));
const section = computed(() =>
  props.category && id.value && ctx.route.query.section === "parent"
    ? "parent"
    : "label",
);
const details = useQuery({
  queryKey: computed(() =>
    ctx.key("get-classification", collection.value, id.value),
  ),
  enabled: computed(
    () => !!id.value && !!ctx.locale.value && !!ctx.tenantId.value,
  ),
  refetchOnWindowFocus: false,
  queryFn: async ({ signal }) =>
    props.category
      ? catalogApi.getCategory(id.value, ctx.locale.value, signal)
      : catalogApi.getTag(id.value, ctx.locale.value, signal),
});
const categories = useQuery({
  queryKey: computed(() => ctx.key("category-options")),
  enabled: computed(
    () => props.category && !!ctx.locale.value && !!ctx.tenantId.value,
  ),
  queryFn: ({ signal }) => loadCategories(ctx.locale.value, signal),
});
const parentId = computed<string | null>(() => {
  const value =
    details.data.value && "parent_id" in details.data.value
      ? details.data.value.parent_id
      : null;
  return typeof value === "string" ? value : null;
});
const failure = computed(() =>
  details.isError.value
    ? getApiErrorStatus(details.error.value) === 404
      ? "Объект не найден."
      : getApiErrorStatus(details.error.value) === 403
        ? "Нет доступа."
        : "Не удалось загрузить объект."
    : "",
);
watch(
  () => [id.value, ctx.locale.value, props.category],
  () => {
    dirty.value = {};
    error.value = "";
    conflict.value = false;
  },
);
watch(section, (_next, previous) => {
  dirty.value[previous] = false;
});
function recordError(e: unknown) {
  error.value = getApiErrorMessage(
    e,
    "Запись не подтверждена. Загрузите актуальное состояние.",
  );
  conflict.value =
    getApiErrorStatus(e) === 409 ||
    getApiErrorStatus(e) === null ||
    (getApiErrorStatus(e) ?? 0) >= 500;
}
async function act(key: "label" | "parent", fn: () => Promise<unknown>) {
  if (pending.value || conflict.value) return;
  const current = ctx.captureSession();
  pending.value = true;
  error.value = "";
  try {
    await fn();
    if (!current()) return;
    const result = await details.refetch();
    if (!current()) return;
    if (result.isError) throw result.error;
    await cache.invalidateQueries({
      queryKey: ["catalog", ctx.tenantId.value],
      refetchType: "none",
    });
    if (!current()) return;
    resets.value[key]++;
    dirty.value[key] = false;
  } catch (e) {
    if (current()) recordError(e);
  } finally {
    if (current()) pending.value = false;
  }
}
async function saveLabel(label: string) {
  const d = details.data.value;
  if (id.value && d) {
    await act("label", () =>
      props.category
        ? catalogApi.putCategoryContent(d.id, ctx.locale.value, {
            expected_revision: d.revision,
            label,
          })
        : catalogApi.putTagTranslation(d.id, ctx.locale.value, {
            expected_revision: d.revision,
            label,
          }),
    );
    return;
  }
  if (pending.value || conflict.value) return;
  const current = ctx.captureSession();
  pending.value = true;
  error.value = "";
  try {
    const result = props.category
      ? await catalogApi.createCategory({
          locale: ctx.locale.value,
          label,
          parent_id: String(ctx.route.query.parent ?? "") || null,
        })
      : await catalogApi.createTag({ locale: ctx.locale.value, label });
    if (!current()) return;
    dirty.value = {};
    pending.value = false;
    await cache.invalidateQueries({
      queryKey: ["catalog", ctx.tenantId.value],
      refetchType: "none",
    });
    if (!current()) return;
    await ctx.router.push({
      path: `/catalog/${collection.value}/${result.id}`,
      query: { locale: ctx.locale.value },
    });
  } catch (e) {
    if (current()) recordError(e);
  } finally {
    if (current()) pending.value = false;
  }
}
function move(parent: string | null) {
  const d = details.data.value;
  if (d)
    void act("parent", () =>
      catalogApi.moveCategory(d.id, {
        expected_revision: d.revision,
        parent_id: parent,
      }),
    );
}
async function reload() {
  if (pending.value) return;
  if (
    Object.values(dirty.value).some(Boolean) &&
    !window.confirm(
      "Загрузить актуальное состояние и отменить локальные изменения?",
    )
  )
    return;
  const current = ctx.captureSession();
  const result = await details.refetch();
  if (!current() || result.isError) return;
  if (props.category) await categories.refetch();
  if (!current()) return;
  dirty.value = {};
  conflict.value = false;
  error.value = "";
  resets.value.label++;
  resets.value.parent++;
}
async function remove() {
  const d = details.data.value;
  if (
    !d ||
    pending.value ||
    conflict.value ||
    !window.confirm(`Удалить «${d.label ?? d.id}»?`)
  )
    return;
  const current = ctx.captureSession();
  pending.value = true;
  error.value = "";
  try {
    if (props.category) await catalogApi.deleteCategory(d.id, d.revision);
    else await catalogApi.deleteTag(d.id, d.revision);
    if (!current()) return;
    await cache.invalidateQueries({
      queryKey: ["catalog", ctx.tenantId.value],
      refetchType: "none",
    });
    if (!current()) return;
    dirty.value = {};
    pending.value = false;
    await ctx.router.push({
      path: `/catalog/${collection.value}`,
      query: { locale: ctx.locale.value },
    });
  } catch (e) {
    if (current()) recordError(e);
  } finally {
    if (current()) pending.value = false;
  }
}
</script>
<template>
  <div class="max-w-3xl space-y-6 p-6">
    <CatalogHeader
      :title="
        category
          ? id
            ? 'Категория'
            : 'Новая категория'
          : id
            ? 'Метка'
            : 'Новая метка'
      "
      :description="
        details.data.value
          ? `Ревизия ${details.data.value.revision}`
          : 'Независимые локализованные подписи'
      "
    />
    <CatalogToolbar
      :locale="ctx.locale.value"
      :options="ctx.options.value"
      @locale="ctx.selectLocale"
    />
    <div
      v-if="error || failure"
      role="alert"
      class="space-y-3 rounded-md border border-destructive p-3"
    >
      <p>{{ error || failure }}</p>
      <p v-if="conflict">Ввод сохранён. Загрузите актуальное состояние.</p>
      <Button v-if="id" variant="outline" :disabled="pending" @click="reload"
        >Загрузить актуальное состояние</Button
      ><Button
        v-else
        variant="outline"
        :disabled="pending"
        @click="
          ctx.router.push({
            path: `/catalog/${collection}`,
            query: { locale: ctx.locale.value },
          })
        "
        >Проверить список</Button
      >
    </div>
    <p v-if="id && details.isPending.value && ctx.locale.value">Загрузка…</p>
    <template
      v-if="ctx.locale.value && (!id || details.data.value) && !failure"
    >
      <nav v-if="category && id" class="flex flex-wrap gap-2">
        <Button
          v-for="tab in [
            { id: 'label', label: 'Название' },
            { id: 'parent', label: 'Место в дереве' },
          ]"
          :key="tab.id"
          :disabled="pending"
          :variant="section === tab.id ? 'default' : 'outline'"
          @click="
            ctx.router.replace({
              query: { ...ctx.route.query, section: tab.id },
            })
          "
          >{{ tab.label }}</Button
        >
      </nav>
      <ClassificationLabelForm
        v-if="section === 'label'"
        :key="id + collection + ctx.locale.value + ctx.sessionKey.value"
        :label="details.data.value?.label ?? null"
        :existing="!!id"
        :pending="pending"
        :disabled="!ctx.active.value || conflict"
        :reset="resets.label"
        @dirty="dirty.label = $event"
        @submit="saveLabel"
      />
      <template v-if="section === 'parent' && details.data.value"
        ><p v-if="categories.isError.value" role="alert">
          Не удалось загрузить дерево.
          <Button variant="outline" @click="categories.refetch()"
            >Повторить</Button
          >
        </p>
        <p v-else-if="categories.isPending.value">Загрузка дерева…</p>
        <CategoryParentForm
          v-else-if="categories.data.value"
          :key="id + ctx.sessionKey.value"
          :id="id"
          :parent-id="parentId"
          :categories="categories.data.value"
          :pending="pending"
          :disabled="conflict"
          :reset="resets.parent"
          @dirty="dirty.parent = $event"
          @submit="move"
      /></template>
      <p v-if="category && !id" class="text-sm text-muted-foreground">
        {{
          ctx.route.query.parent
            ? "Создание внутри выбранной ветви."
            : "Создание в корне дерева."
        }}
      </p>
      <Button
        v-if="id"
        variant="ghost"
        :disabled="pending || conflict"
        @click="remove"
        >{{ category ? "Удалить категорию" : "Удалить метку" }}</Button
      >
    </template>
  </div>
</template>
