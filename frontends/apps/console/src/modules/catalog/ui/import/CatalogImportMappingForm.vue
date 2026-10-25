<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  CatalogImportDetails,
  ImportConfiguration,
  ImportMapping,
} from "../../model/import.types";
import {
  importTargets,
  localizedImportTargets,
} from "../../model/import.constants";
import {
  cloneImportConfiguration,
  importMappingPreview,
} from "../../model/import.draft";
const props = defineProps<{
  detail: CatalogImportDetails;
  value: ImportConfiguration;
  pending: boolean;
  dirty: boolean;
}>();
const emit = defineEmits<{
  change: [value: ImportConfiguration];
  preview: [];
  start: [];
}>();
function setting<K extends keyof ImportConfiguration>(
  key: K,
  value: ImportConfiguration[K],
): void {
  emit("change", {
    ...cloneImportConfiguration(props.value),
    [key]: value,
    ...(key === "recordPath" ? { mappings: [] } : {}),
  });
}
function mapping(index: number, patch: Partial<ImportMapping>): void {
  const next = cloneImportConfiguration(props.value);
  next.mappings[index] = { ...next.mappings[index]!, ...patch };
  if (!localizedImportTargets.has(next.mappings[index]!.target))
    next.mappings[index]!.locale = null;
  emit("change", next);
}
function remove(index: number): void {
  setting(
    "mappings",
    props.value.mappings.filter((_m, i) => i !== index),
  );
}
function add(): void {
  const target =
    importTargets.find(
      ([key]) => !props.value.mappings.some((m) => m.target === key),
    )?.[0] ?? "title";
  setting("mappings", [
    ...props.value.mappings,
    { target, source: null, constant: "", locale: null },
  ]);
}
const unmapped = computed(
  () =>
    props.detail.analysis.fields.filter(
      (f) => !props.value.mappings.some((m) => m.source === f.id),
    ).length,
);
const preview = computed(() =>
  importMappingPreview(
    props.value,
    props.detail.analysis.samples[0]?.values ?? {},
  ),
);
</script>
<template>
  <div class="flex min-w-0 flex-col gap-6">
    <FieldGroup class="grid gap-4 sm:grid-cols-2">
      <Field
        ><FieldLabel for="import-mode">Режим импорта</FieldLabel>
        <Select
          :model-value="value.mode"
          :disabled="pending"
          @update:model-value="
            (v) => setting('mode', String(v) as ImportConfiguration['mode'])
          "
          ><SelectTrigger id="import-mode"><SelectValue /></SelectTrigger
          ><SelectContent
            ><SelectGroup>
              <SelectItem value="create">Только создание</SelectItem
              ><SelectItem value="update">Только обновление по SKU</SelectItem
              ><SelectItem value="upsert"
                >Создание и обновление по SKU</SelectItem
              >
            </SelectGroup></SelectContent
          ></Select
        >
      </Field>
      <Field
        ><FieldLabel for="import-default-locale">Язык по умолчанию</FieldLabel
        ><Input
          id="import-default-locale"
          :model-value="value.defaultLocale"
          :disabled="pending"
          @update:model-value="(v) => setting('defaultLocale', String(v))"
      /></Field>
      <Field
        ><FieldLabel for="import-timezone">Часовой пояс дат</FieldLabel
        ><Input
          id="import-timezone"
          :model-value="value.timezone"
          :disabled="pending"
          @update:model-value="(v) => setting('timezone', String(v))"
      /></Field>
      <Field orientation="horizontal"
        ><Checkbox
          id="import-clear-empty"
          :model-value="value.clearEmpty"
          :disabled="pending"
          @update:model-value="(v) => setting('clearEmpty', v === true)"
        />
        <div>
          <FieldLabel for="import-clear-empty"
            >Очищать пустые значения</FieldLabel
          ><FieldDescription
            >По умолчанию пустые и несопоставленные поля сохраняют прежние
            данные.</FieldDescription
          >
        </div></Field
      >
    </FieldGroup>
    <FieldGroup
      v-if="detail.analysis.format === 'csv'"
      class="grid gap-4 sm:grid-cols-2"
    >
      <Field
        ><FieldLabel for="import-encoding">Кодировка CSV</FieldLabel
        ><Select
          :model-value="value.encoding ?? 'utf-8-sig'"
          :disabled="pending"
          @update:model-value="(v) => setting('encoding', String(v))"
          ><SelectTrigger id="import-encoding"><SelectValue /></SelectTrigger
          ><SelectContent
            ><SelectGroup
              ><SelectItem value="utf-8-sig">UTF-8 / BOM</SelectItem
              ><SelectItem value="cp1251">Windows-1251</SelectItem></SelectGroup
            ></SelectContent
          ></Select
        ></Field
      >
      <Field
        ><FieldLabel for="import-delimiter">Разделитель CSV</FieldLabel
        ><Select
          :model-value="value.delimiter ?? ','"
          :disabled="pending"
          @update:model-value="(v) => setting('delimiter', String(v))"
          ><SelectTrigger id="import-delimiter"><SelectValue /></SelectTrigger
          ><SelectContent
            ><SelectGroup
              ><SelectItem value=",">Запятая</SelectItem
              ><SelectItem value=";">Точка с запятой</SelectItem
              ><SelectItem :value="'\t'">Табуляция</SelectItem></SelectGroup
            ></SelectContent
          ></Select
        ></Field
      >
    </FieldGroup>
    <FieldGroup v-if="detail.analysis.format === 'xml'"
      ><Field
        ><FieldLabel for="import-record-path">Узел товара в XML</FieldLabel
        ><Select
          :model-value="value.recordPath ?? undefined"
          :disabled="pending"
          @update:model-value="(v) => setting('recordPath', String(v))"
          ><SelectTrigger id="import-record-path" class="max-w-full"
            ><SelectValue
              placeholder="Выберите повторяющийся узел" /></SelectTrigger
          ><SelectContent
            ><SelectGroup
              ><SelectItem
                v-for="path in detail.analysis.candidates"
                :key="path"
                :value="path"
                >{{ path }}</SelectItem
              ></SelectGroup
            ></SelectContent
          ></Select
        ><FieldDescription
          >После смены узла обновите предпросмотр.</FieldDescription
        ></Field
      ></FieldGroup
    >
    <section
      class="flex min-w-0 flex-col gap-3"
      aria-label="Сопоставление полей"
    >
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 class="font-semibold">
            Сопоставление полей
            <Badge variant="secondary">{{
              detail.analysis.format.toUpperCase()
            }}</Badge>
          </h3>
          <p class="text-sm text-muted-foreground">
            {{ detail.run.total }} записей ·
            {{ detail.analysis.fields.length }} полей · {{ unmapped }} не
            сопоставлено
          </p>
        </div>
        <Button variant="outline" size="sm" :disabled="pending" @click="add"
          >Добавить поле / константу</Button
        >
      </div>
      <div class="max-h-96 overflow-auto rounded-md border">
        <Table>
          <TableHeader
            ><TableRow
              ><TableHead>Поле Catalog</TableHead
              ><TableHead>Поле источника / константа</TableHead
              ><TableHead>Язык</TableHead
              ><TableHead
                ><span class="sr-only">Действия</span></TableHead
              ></TableRow
            ></TableHeader
          >
          <TableBody
            ><TableRow v-for="(m, index) in value.mappings" :key="index">
              <TableCell
                ><Select
                  :model-value="m.target"
                  :disabled="pending"
                  @update:model-value="
                    (v) => mapping(index, { target: String(v) })
                  "
                  ><SelectTrigger
                    class="min-w-44"
                    :aria-label="`Поле Catalog ${index + 1}`"
                    ><SelectValue /></SelectTrigger
                  ><SelectContent
                    ><SelectGroup
                      ><SelectItem
                        v-for="[key, label] in importTargets"
                        :key="key"
                        :value="key"
                        >{{ label }}</SelectItem
                      ></SelectGroup
                    ></SelectContent
                  ></Select
                ></TableCell
              >
              <TableCell
                ><Select
                  :model-value="m.source ?? '__constant'"
                  :disabled="pending"
                  @update:model-value="
                    (v) =>
                      mapping(
                        index,
                        v === '__constant'
                          ? { source: null, constant: '' }
                          : { source: String(v), constant: null },
                      )
                  "
                  ><SelectTrigger
                    class="min-w-52 max-w-80"
                    :aria-label="`Источник ${index + 1}`"
                    ><SelectValue /></SelectTrigger
                  ><SelectContent
                    ><SelectGroup
                      ><SelectItem value="__constant"
                        >Постоянное значение</SelectItem
                      ><SelectItem
                        v-for="(field, column) in detail.analysis.fields"
                        :key="field.id"
                        :value="field.id"
                        >{{ column + 1 }}. {{ field.label }}</SelectItem
                      ></SelectGroup
                    ></SelectContent
                  ></Select
                ><Input
                  v-if="m.constant !== null"
                  class="mt-2"
                  :aria-label="`Константа ${index + 1}`"
                  :model-value="m.constant"
                  :disabled="pending"
                  @update:model-value="
                    (v) => mapping(index, { constant: String(v) })
                  "
              /></TableCell>
              <TableCell
                ><Input
                  v-if="localizedImportTargets.has(m.target)"
                  class="min-w-24"
                  :aria-label="`Язык ${index + 1}`"
                  :placeholder="
                    m.target === 'images' ? 'Все языки' : value.defaultLocale
                  "
                  :model-value="m.locale ?? ''"
                  :disabled="pending"
                  @update:model-value="
                    (v) => mapping(index, { locale: String(v) || null })
                  "
                /><span v-else class="text-muted-foreground">—</span></TableCell
              >
              <TableCell
                ><Button
                  variant="ghost"
                  size="sm"
                  :disabled="pending"
                  :aria-label="`Не импортировать ${m.target} ${index + 1}`"
                  @click="remove(index)"
                  >Убрать</Button
                ></TableCell
              >
            </TableRow></TableBody
          >
        </Table>
      </div>
      <p class="text-sm text-muted-foreground">
        Категории, характеристики и внешние ID остаются несопоставленными. Новые
        товары создаются черновиками.
      </p>
    </section>
    <details class="min-w-0 rounded-md border p-3">
      <summary class="cursor-pointer font-medium">
        Предпросмотр источника — первые
        {{ detail.analysis.samples.length }} записей
      </summary>
      <div class="mt-3 max-h-72 overflow-auto">
        <Table
          ><TableHeader
            ><TableRow
              ><TableHead>№</TableHead
              ><TableHead
                v-for="field in detail.analysis.fields"
                :key="field.id"
                >{{ field.label }}</TableHead
              ></TableRow
            ></TableHeader
          ><TableBody
            ><TableRow
              v-for="sample in detail.analysis.samples"
              :key="sample.number"
              ><TableCell>{{ sample.number }}</TableCell
              ><TableCell
                v-for="field in detail.analysis.fields"
                :key="field.id"
                ><p
                  class="max-w-64 truncate"
                  :title="sample.values[field.id]?.join(', ')"
                >
                  {{ sample.values[field.id]?.join(", ").slice(0, 160) || "—" }}
                </p></TableCell
              ></TableRow
            ></TableBody
          ></Table
        >
      </div>
    </details>
    <details class="rounded-md border p-3">
      <summary class="cursor-pointer font-medium">
        Пример сопоставления первой записи
      </summary>
      <dl class="mt-3 grid gap-2 text-sm sm:grid-cols-[12rem_1fr]">
        <template v-for="(entries, key) in preview" :key="key"
          ><dt class="font-medium">{{ key }}</dt>
          <dd class="break-all text-muted-foreground">
            {{ entries.join(", ").slice(0, 350) || "Очистить значение" }}
          </dd></template
        >
      </dl>
    </details>
    <div class="flex flex-wrap justify-end gap-3">
      <Button variant="outline" :disabled="pending" @click="emit('preview')">{{
        pending ? "Подготовка…" : "Обновить предпросмотр"
      }}</Button
      ><Button
        :disabled="
          pending || dirty || !value.mappings.length || !detail.run.total
        "
        @click="emit('start')"
        >Запустить импорт</Button
      >
    </div>
    <p v-if="dirty" class="text-right text-sm text-muted-foreground">
      Сначала обновите предпросмотр, чтобы подтвердить изменения.
    </p>
  </div>
</template>
