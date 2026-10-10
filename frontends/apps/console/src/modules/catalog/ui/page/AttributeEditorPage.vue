<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
import { catalogApi } from "../../api/catalog.api";
import { attributeFromDto } from "../../api/catalog.mapper";
import type { AttributeOptionDraft } from "../../model/catalog.types";
import { useCatalogContext } from "../../model/use-catalog-context";
import CatalogHeader from "../CatalogHeader.vue";
import CatalogToolbar from "../CatalogToolbar.vue";
import AttributeLabelForm from "../forms/AttributeLabelForm.vue";
import AttributeOptionsForm from "../forms/AttributeOptionsForm.vue";
const dirty = ref<Record<string, boolean>>({}),
  pending = ref(false),
  error = ref(""),
  conflict = ref(false),
  resets = ref({ label: 0, options: 0 });
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
const id = computed(() => String(ctx.route.params.attributeId ?? ""));
const attribute = useQuery({
  queryKey: computed(() => ctx.key("get-attribute", id.value)),
  enabled: computed(
    () => !!id.value && !!ctx.locale.value && !!ctx.tenantId.value,
  ),
  refetchOnWindowFocus: false,
  queryFn: ({ signal }) =>
    catalogApi.getAttribute(id.value, ctx.locale.value, signal),
  select: attributeFromDto,
});
const section = computed(() =>
  ctx.route.query.section === "options" && id.value ? "options" : "label",
);
const failure = computed(() =>
  attribute.isError.value
    ? getApiErrorStatus(attribute.error.value) === 404
      ? "Характеристика не найдена."
      : getApiErrorStatus(attribute.error.value) === 403
        ? "Нет доступа к характеристике."
        : "Не удалось загрузить характеристику."
    : "",
);
watch(
  () => [id.value, ctx.locale.value],
  () => {
    dirty.value = {};
    error.value = "";
    conflict.value = false;
  },
);
watch(section, (_next, previous) => {
  dirty.value[previous] = false;
});
async function act(key: "label" | "options", fn: () => Promise<unknown>) {
  if (pending.value || conflict.value) return;
  const current = ctx.captureSession();
  pending.value = true;
  error.value = "";
  try {
    await fn();
    if (!current()) return;
    const result = await attribute.refetch();
    if (!current()) return;
    if (result.isError) throw result.error;
    await cache.invalidateQueries({
      queryKey: ["catalog", ctx.tenantId.value],
      refetchType: "none",
    });
    resets.value[key]++;
    dirty.value[key] = false;
  } catch (e) {
    if (!current()) return;
    error.value = getApiErrorMessage(
      e,
      "Сохранение не подтверждено. Загрузите актуальное состояние.",
    );
    conflict.value =
      getApiErrorStatus(e) === 409 ||
      getApiErrorStatus(e) === null ||
      (getApiErrorStatus(e) ?? 0) >= 500;
  } finally {
    if (current()) pending.value = false;
  }
}
async function label(code: string, value: string) {
  if (id.value) {
    const a = attribute.data.value;
    if (a)
      await act("label", () =>
        catalogApi.putAttributeTranslation(a.id, ctx.locale.value, {
          expected_revision: a.revision,
          label: value,
        }),
      );
    return;
  }
  if (pending.value) return;
  const current = ctx.captureSession();
  pending.value = true;
  error.value = "";
  try {
    const result = await catalogApi.createAttribute({
      code,
      locale: ctx.locale.value,
      label: value,
    });
    if (!current()) return;
    dirty.value = {};
    pending.value = false;
    await cache.invalidateQueries({
      queryKey: ["catalog", ctx.tenantId.value],
      refetchType: "none",
    });
    await ctx.router.push({
      path: `/catalog/attributes/${result.id}`,
      query: { locale: ctx.locale.value, section: "options" },
    });
  } catch (e) {
    if (current())
      error.value = getApiErrorMessage(
        e,
        "Создание не подтверждено. Проверьте список перед повтором.",
      );
  } finally {
    if (current()) pending.value = false;
  }
}
function options(values: AttributeOptionDraft[]) {
  const a = attribute.data.value;
  if (a)
    void act("options", () =>
      catalogApi.replaceAttributeOptions(a.id, ctx.locale.value, {
        expected_revision: a.revision,
        options: values.map((o) => ({
          option_id: o.id,
          code: o.code,
          label: o.label,
        })),
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
  const current = ctx.captureSession(),
    result = await attribute.refetch();
  if (!current() || result.isError) return;
  dirty.value = {};
  error.value = "";
  conflict.value = false;
  resets.value.label++;
  resets.value.options++;
}
async function remove() {
  const a = attribute.data.value;
  if (
    !a ||
    pending.value ||
    conflict.value ||
    !window.confirm(
      `Удалить характеристику «${a.label ?? a.code}» и её значения?`,
    )
  )
    return;
  const current = ctx.captureSession();
  pending.value = true;
  try {
    await catalogApi.deleteAttribute(a.id, a.revision);
    if (!current()) return;
    dirty.value = {};
    pending.value = false;
    await ctx.router.push({
      path: "/catalog/attributes",
      query: { locale: ctx.locale.value },
    });
  } catch (e) {
    if (current())
      error.value = getApiErrorMessage(e, "Удаление не подтверждено.");
  } finally {
    if (current()) pending.value = false;
  }
}
</script>
<template>
  <div class="max-w-3xl space-y-6 p-6">
    <CatalogHeader
      :title="id ? 'Enum-характеристика' : 'Новая enum-характеристика'"
      description="Устойчивые определения и значения для осей VARIABLE."
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
      <p v-if="conflict" class="text-sm">
        Ввод сохранён. Загрузите актуальное состояние для продолжения.
      </p>
      <Button v-if="id" variant="outline" :disabled="pending" @click="reload"
        >Загрузить актуальное состояние</Button
      >
    </div>
    <p v-if="id && attribute.isPending.value && ctx.locale.value">Загрузка…</p>
    <template
      v-if="ctx.locale.value && (!id || attribute.data.value) && !failure"
    >
      <nav v-if="id" class="flex flex-wrap gap-2">
        <Button
          v-for="tab in [
            { id: 'label', label: 'Подпись' },
            { id: 'options', label: 'Значения' },
          ]"
          :key="tab.id"
          :variant="section === tab.id ? 'default' : 'outline'"
          :disabled="pending"
          @click="
            ctx.router.replace({
              query: { ...ctx.route.query, section: tab.id },
            })
          "
          >{{ tab.label }}</Button
        >
      </nav>
      <AttributeLabelForm
        v-if="section === 'label'"
        :key="id + ctx.locale.value + ctx.sessionKey.value"
        :code="attribute.data.value?.code ?? ''"
        :label="attribute.data.value?.label ?? null"
        :existing="!!id"
        :pending="pending"
        :disabled="!ctx.active.value || conflict"
        :reset="resets.label"
        @dirty="dirty.label = $event"
        @submit="label"
      />
      <AttributeOptionsForm
        v-if="section === 'options' && attribute.data.value"
        :key="id + ctx.locale.value + ctx.sessionKey.value"
        :options="attribute.data.value.options"
        :pending="pending"
        :disabled="!ctx.active.value || conflict"
        :reset="resets.options"
        @dirty="dirty.options = $event"
        @submit="options"
      />
      <p v-if="!ctx.active.value" class="text-sm text-muted-foreground">
        Locale неактивна: подписи доступны для чтения, запись отключена.
      </p>
      <Button
        v-if="id"
        variant="ghost"
        :disabled="pending || conflict"
        @click="remove"
        >Удалить характеристику</Button
      >
    </template>
  </div>
</template>
