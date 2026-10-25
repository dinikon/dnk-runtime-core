<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Plus } from "@lucide/vue";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";
import CatalogImportMappingRow from "./CatalogImportMappingRow.vue";
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
    <FieldGroup v-if="detail.analysis.format === 'xml'"
      ><Field
        ><FieldLabel for="import-record-path">Узел товара в XML</FieldLabel
        ><Select
          :model-value="value.recordPath ?? undefined"
          :disabled="pending"
          @update:model-value="(v) => setting('recordPath', String(v))"
          ><SelectTrigger
            id="import-record-path"
            class="min-h-11 w-full max-w-full"
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
      class="flex min-w-0 flex-col gap-1"
      aria-label="Сопоставление полей"
    >
      <div class="flex items-center justify-between gap-3 pb-2">
        <div class="min-w-0">
          <h3 class="font-semibold tracking-tight">Сопоставление полей</h3>
          <p class="text-sm text-muted-foreground">
            {{ detail.run.total }} записей ·
            {{ detail.analysis.format.toUpperCase() }} · {{ unmapped }} не
            сопоставлено
          </p>
        </div>
        <Button
          variant="outline"
          class="h-11 shrink-0"
          :disabled="pending"
          @click="add"
          ><Plus data-icon="inline-start" />Добавить</Button
        >
      </div>
      <FieldGroup class="gap-0"
        ><CatalogImportMappingRow
          v-for="(m, index) in value.mappings"
          :key="index"
          :value="m"
          :index="index"
          :fields="detail.analysis.fields"
          :default-locale="value.defaultLocale"
          :pending="pending"
          @change="(patch) => mapping(index, patch)"
          @remove="remove(index)"
      /></FieldGroup>
      <p class="pt-2 text-xs leading-relaxed text-muted-foreground">
        Категории, характеристики и внешние ID остаются несопоставленными. Новые
        товары создаются черновиками.
      </p>
    </section>
    <Accordion type="single" collapsible
      ><AccordionItem value="settings"
        ><AccordionTrigger>Параметры импорта</AccordionTrigger
        ><AccordionContent
          ><div class="flex flex-col gap-5 pt-2">
            <FieldGroup class="grid gap-4 sm:grid-cols-2">
              <Field
                ><FieldLabel for="import-mode">Режим импорта</FieldLabel>
                <Select
                  :model-value="value.mode"
                  :disabled="pending"
                  @update:model-value="
                    (v) =>
                      setting('mode', String(v) as ImportConfiguration['mode'])
                  "
                  ><SelectTrigger id="import-mode"
                    ><SelectValue /></SelectTrigger
                  ><SelectContent
                    ><SelectGroup>
                      <SelectItem value="create">Только создание</SelectItem
                      ><SelectItem value="update"
                        >Только обновление по SKU</SelectItem
                      ><SelectItem value="upsert"
                        >Создание и обновление по SKU</SelectItem
                      >
                    </SelectGroup></SelectContent
                  ></Select
                >
              </Field>
              <Field
                ><FieldLabel for="import-default-locale"
                  >Язык по умолчанию</FieldLabel
                ><Input
                  id="import-default-locale"
                  :model-value="value.defaultLocale"
                  :disabled="pending"
                  @update:model-value="
                    (v) => setting('defaultLocale', String(v))
                  "
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
                    >По умолчанию пустые и несопоставленные поля сохраняют
                    прежние данные.</FieldDescription
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
                  ><SelectTrigger id="import-encoding"
                    ><SelectValue /></SelectTrigger
                  ><SelectContent
                    ><SelectGroup
                      ><SelectItem value="utf-8-sig">UTF-8 / BOM</SelectItem
                      ><SelectItem value="cp1251"
                        >Windows-1251</SelectItem
                      ></SelectGroup
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
                  ><SelectTrigger id="import-delimiter"
                    ><SelectValue /></SelectTrigger
                  ><SelectContent
                    ><SelectGroup
                      ><SelectItem value=",">Запятая</SelectItem
                      ><SelectItem value=";">Точка с запятой</SelectItem
                      ><SelectItem :value="'\t'"
                        >Табуляция</SelectItem
                      ></SelectGroup
                    ></SelectContent
                  ></Select
                ></Field
              >
            </FieldGroup>
          </div></AccordionContent
        ></AccordionItem
      ></Accordion
    >
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
  </div>
</template>
