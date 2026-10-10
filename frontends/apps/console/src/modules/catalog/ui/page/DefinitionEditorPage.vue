<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
import { catalogApi } from "../../api/catalog.api";
import { typeFromDto, blockFromDto } from "../../api/catalog.mapper";
import { loadBlocks } from "../../model/catalog-options";
import { useCatalogContext } from "../../model/use-catalog-context";
import type { DefinitionInput, BlockLink } from "../../model/catalog.types";
import CatalogHeader from "../CatalogHeader.vue";
import CatalogToolbar from "../CatalogToolbar.vue";
import DefinitionForm from "../forms/DefinitionForm.vue";
import SchemaForm from "../forms/SchemaForm.vue";
const props = defineProps<{ block: boolean }>();
const dirty = ref({ definition: false, schema: false }),
  pending = ref(false),
  error = ref(""),
  conflict = ref(false),
  reset = ref(0),
  schemaReset = ref(0);
const ctx = useCatalogContext(
  () => dirty.value.definition || dirty.value.schema,
  () => pending.value,
  () => {
    dirty.value = { definition: false, schema: false };
    error.value = "";
    pending.value = false;
    conflict.value = false;
  },
);
const id = computed(() => String(ctx.route.params.definitionId ?? "")),
  isNew = computed(() => !id.value || id.value === "new");
const definition = useQuery({
  queryKey: computed(() =>
    ctx.key(props.block ? "get-block" : "get-type", id.value),
  ),
  enabled: computed(
    () => !isNew.value && !!ctx.locale.value && !!ctx.tenantId.value,
  ),
  refetchOnWindowFocus: false,
  queryFn: async ({ signal }) =>
    props.block
      ? blockFromDto(
          await catalogApi.getContentBlock(id.value, ctx.locale.value, signal),
        )
      : typeFromDto(
          await catalogApi.getProductType(id.value, ctx.locale.value, signal),
        ),
});
const blocks = useQuery({
  queryKey: computed(() => ctx.key("block-options")),
  enabled: computed(
    () => !props.block && !!ctx.locale.value && !!ctx.tenantId.value,
  ),
  queryFn: ({ signal }) => loadBlocks(ctx.locale.value, signal),
});
const links = computed(() => {
  const d = definition.data.value;
  return d && "blocks" in d ? d.blocks : [];
});
const disabled = computed(
  () =>
    !ctx.active.value ||
    definition.data.value?.system === true ||
    conflict.value,
);
const readError = computed(() =>
  definition.isError.value
    ? getApiErrorStatus(definition.error.value) === 404
      ? "Определение не найдено."
      : getApiErrorStatus(definition.error.value) === 403
        ? "Нет доступа."
        : "Не удалось загрузить определение."
    : "",
);
watch(
  () => [ctx.locale.value, id.value, props.block],
  () => {
    dirty.value = { definition: false, schema: false };
    error.value = "";
    conflict.value = false;
    reset.value++;
    schemaReset.value++;
  },
);
async function save(input: DefinitionInput) {
  const current = ctx.captureSession();
  if (pending.value || disabled.value) return;
  pending.value = true;
  error.value = "";
  try {
    if (isNew.value) {
      const d = props.block
        ? await catalogApi.createContentBlock({
            code: input.code,
            locale: ctx.locale.value,
            label: input.label,
            value_type: input.valueType,
          })
        : await catalogApi.createProductType({
            code: input.code,
            locale: ctx.locale.value,
            label: input.label,
            blocks: [],
          });
      if (!current()) return;
      dirty.value.definition = false;
      pending.value = false;
      await ctx.router.push({
        path: `/catalog/${props.block ? "content-blocks" : "product-types"}/${d.id}`,
        query: { locale: ctx.locale.value },
      });
      if (!current()) return;
    } else {
      const d = definition.data.value!;
      if (props.block) {
        await catalogApi.updateContentBlock(d.id, {
          expected_revision: d.revision,
          locale: ctx.locale.value,
          label: input.label,
          value_type: input.valueType,
        });
      } else {
        await catalogApi.putProductTypeTranslation(d.id, ctx.locale.value, {
          expected_revision: d.revision,
          label: input.label,
        });
      }
      if (!current()) return;
      await definition.refetch();
      if (!current()) return;
      reset.value++;
      dirty.value.definition = false;
    }
  } catch (e) {
    if (!current()) return;
    conflict.value =
      getApiErrorStatus(e) === 409 ||
      getApiErrorStatus(e) === null ||
      (getApiErrorStatus(e) ?? 0) >= 500;
    error.value = getApiErrorMessage(
      e,
      "Сохранение не подтверждено. Загрузите актуальное состояние.",
    );
  } finally {
    if (current()) pending.value = false;
  }
}
async function saveSchema(links: BlockLink[]) {
  const current = ctx.captureSession();
  const d = definition.data.value;
  if (!d || !("schemaVersion" in d) || pending.value || disabled.value) return;
  pending.value = true;
  error.value = "";
  try {
    await catalogApi.replaceProductTypeSchema(d.id, {
      expected_revision: d.revision,
      expected_schema_version: d.schemaVersion,
      blocks: links.map((b) => ({
        block_id: b.blockId,
        scope: b.scope,
        required: b.required,
        position: b.position,
      })),
    });
    if (!current()) return;
    await definition.refetch();
    if (!current()) return;
    schemaReset.value++;
    dirty.value.schema = false;
  } catch (e) {
    if (!current()) return;
    conflict.value =
      getApiErrorStatus(e) === 409 ||
      getApiErrorStatus(e) === null ||
      (getApiErrorStatus(e) ?? 0) >= 500;
    error.value = getApiErrorMessage(e, "Схема не сохранена.");
  } finally {
    if (current()) pending.value = false;
  }
}
async function reload() {
  const current = ctx.captureSession();
  if (
    (dirty.value.definition || dirty.value.schema) &&
    !window.confirm(
      "Загрузить актуальное состояние и отменить локальные изменения?",
    )
  )
    return;
  const r = await definition.refetch();
  if (!current()) return;
  if (r.isError) return;
  conflict.value = false;
  error.value = "";
  dirty.value = { definition: false, schema: false };
  reset.value++;
  schemaReset.value++;
}
async function remove() {
  const current = ctx.captureSession();
  const d = definition.data.value;
  if (
    !d ||
    pending.value ||
    !window.confirm(
      "Удалить определение? Используемые определения защищены сервером.",
    )
  )
    return;
  pending.value = true;
  try {
    if (props.block) {
      await catalogApi.deleteContentBlock(d.id, d.revision);
    } else {
      await catalogApi.deleteProductType(d.id, d.revision);
    }
    if (!current()) return;
    dirty.value = { definition: false, schema: false };
    pending.value = false;
    await ctx.router.push({
      path: `/catalog/${props.block ? "content-blocks" : "product-types"}`,
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
      :title="
        (isNew ? 'Новое определение: ' : '') +
        (block ? 'Блок контента' : 'Тип контента')
      "
      description="Стабильная идентичность и подпись для каждого явного языка."
    /><CatalogToolbar
      :locale="ctx.locale.value"
      :options="ctx.options.value"
      @locale="ctx.selectLocale"
    />
    <div v-if="error || readError" role="alert" class="rounded-md border p-4">
      <p>{{ error || readError }}</p>
      <p v-if="conflict" class="mt-2">
        Ввод сохранён. Требуется явное обновление.
      </p>
      <Button
        v-if="!isNew"
        variant="outline"
        class="mt-3"
        :disabled="pending"
        @click="reload"
        >Загрузить актуальное состояние</Button
      >
    </div>
    <p
      v-if="definition.data.value?.system"
      class="rounded-md bg-muted p-3 text-sm"
    >
      Системное определение защищено. Создайте пользовательское определение для
      своей схемы.
    </p>
    <template
      v-if="ctx.locale.value && (isNew || definition.data.value) && !readError"
      ><DefinitionForm
        :key="id + ctx.locale.value + ctx.sessionKey.value"
        :block="block"
        :code="definition.data.value?.code"
        :label="definition.data.value?.label"
        :value-type="
          definition.data.value && 'valueType' in definition.data.value
            ? definition.data.value.valueType
            : undefined
        "
        :disabled="disabled"
        :pending="pending"
        :reset="reset"
        @dirty="dirty.definition = $event"
        @submit="save"
      />
      <section
        v-if="!block && !isNew && definition.data.value"
        class="space-y-4 border-t pt-6"
      >
        <h2 class="text-lg font-semibold">Схема контента</h2>
        <p v-if="blocks.isError.value" role="alert">
          Не удалось загрузить блоки.
        </p>
        <SchemaForm
          v-if="blocks.data.value"
          :key="id + ctx.locale.value + ctx.sessionKey.value"
          :links="links"
          :blocks="blocks.data.value"
          :disabled="disabled"
          :pending="pending"
          :reset="schemaReset"
          @dirty="dirty.schema = $event"
          @submit="saveSchema"
        />
      </section>
      <Button
        v-if="!isNew && !definition.data.value?.system"
        variant="ghost"
        :disabled="pending"
        @click="remove"
        >Удалить определение</Button
      ></template
    >
  </div>
</template>
