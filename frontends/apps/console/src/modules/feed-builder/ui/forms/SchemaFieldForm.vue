<script setup lang="ts">
import { computed } from "vue";
import { ArrowUp, ArrowDown, X } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Field,
  FieldSet,
  FieldLegend,
  FieldGroup,
  FieldLabel,
  FieldDescription,
  FieldError,
} from "@/components/ui/field";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import PriceCalculationForm from "./PriceCalculationForm.vue";
import { initialCalculation } from "../../model/feed-calculation.draft";
import type { CalculationMetadata } from "../../model/feed-calculation.types";
import type { CatalogCategory } from "@/modules/catalog";
import type { CategoryType } from "../../model/feed-categories.types";
import CategoryFieldSettings from "./CategoryFieldSettings.vue";
import ScalarFieldSettings from "./ScalarFieldSettings.vue";
import SchemaTransformsForm from "./SchemaTransformsForm.vue";
import { cloneSchemaValue } from "../../model/feed-schema.clone";
import { fieldIsReadonly } from "../../model/feed-schema.draft";
import type {
  SchemaFieldDraft,
  SchemaMetadata,
  SchemaIssue,
  TextTypeDraft,
  MoneyTypeDraft,
  ScalarTypeDraft,
  FallbackMode,
  SourcePath,
} from "../../model/feed-schema.types";
const props = defineProps<{
  field: SchemaFieldDraft;
  metadata: SchemaMetadata;
  issues: SchemaIssue[];
  disabled: boolean;
  xmlItemName?: string;
  calculationMetadata?: CalculationMetadata;
  catalogCategories?: CatalogCategory[];
  catalogLoading?: boolean;
  catalogError?: boolean;
  savedCategoryIds?: string[];
}>();
const emit = defineEmits<{ change: [field: SchemaFieldDraft]; retryCatalog: [] }>();
const locked = computed(() => props.disabled || fieldIsReadonly(props.field));
const isXmlAttribute = computed(
  () => !!props.xmlItemName && props.field.export.xmlPlacement === "ATTRIBUTE",
);
const category = computed(() => props.field.typeDefinition.kind === "category" ? props.field.typeDefinition : undefined);
const scalar = computed(() => {
  const value = props.field.typeDefinition;
  return value.kind === "integer" || value.kind === "boolean" ? value : undefined;
});
const type = computed(() => {
  const value = props.field.typeDefinition;
  return value.kind === "integer" || value.kind === "boolean" || value.kind === "category" ? undefined : value;
});
const mode = computed(() =>
  type.value?.kind === "money" ? type.value.value.mode : type.value?.value.kind,
);
const source = computed(() =>
  type.value && "source" in type.value.value ? type.value.value.source.path : "",
);
const sourceOptions = computed(() =>
  props.metadata.sources.filter((entry) => entry.fieldKinds.includes(props.field.typeDefinition.kind)),
);
const editableModes = computed(() =>
  props.metadata.fieldTypes.find((entry) => entry.kind === props.field.typeDefinition.kind)?.editableModes ?? [],
);
const textSettings = computed(() => type.value?.kind === "money" ? undefined : type.value);
const fallbackOptions = computed(() => props.metadata.locales.filter((entry) =>
  entry.code !== textSettings.value?.locale && !textSettings.value?.fallbackPolicy?.locales.includes(entry.code),
));
const currentLocaleUnavailable = computed(() =>
  textSettings.value?.locale && !props.metadata.locales.some((entry) => entry.code === textSettings.value?.locale),
);
const localized = computed(
  () =>
    mode.value === "MANUAL" ||
    props.metadata.sources.find((s) => s.path === source.value)
      ?.requiresLocale === true,
);
function change(update: (field: SchemaFieldDraft) => void): void {
  if (locked.value) return;
  const field = cloneSchemaValue(props.field);
  update(field);
  emit("change", field);
}
function textChange(update: (type: TextTypeDraft) => void): void {
  change((f) => {
    if (f.typeDefinition.kind === "string" || f.typeDefinition.kind === "text")
      update(f.typeDefinition);
  });
}
function moneyChange(update: (type: MoneyTypeDraft) => void): void {
  change((f) => {
    if (f.typeDefinition.kind === "money") update(f.typeDefinition);
  });
}
function setMode(value: string): void {
  if (!["SOURCE", "MANUAL", "CALCULATED", "CONSTANT"].includes(value)) return;
  if (value === "CONSTANT") {
    textChange((t) => {
      t.value = { kind: "CONSTANT", value: "" };
      t.locale = null;
      t.fallbackPolicy = null;
    });
    return;
  }
  if (value === "CALCULATED") {
    if (!props.calculationMetadata) return;
    moneyChange((t) => {
      t.value = {
        kind: "MONEY",
        mode: "CALCULATED",
        calculation: initialCalculation(),
      };
    });
    return;
  }
  change((f) => {
    const settings = f.typeDefinition;
    if (settings.kind === "integer" || settings.kind === "boolean" || settings.kind === "category") return;
    settings.value =
      settings.kind === "money"
        ? value === "SOURCE"
          ? {
              kind: "MONEY",
              mode: "SOURCE",
              source: { provider: "catalog", path: "item.regular_price" },
            }
          : { kind: "MONEY", mode: "MANUAL" }
        : value === "SOURCE"
          ? { kind: "SOURCE", source: { provider: "catalog", path: "" } }
          : { kind: "MANUAL" };
  });
}
function setConstantValue(value: string): void {
  textChange((type) => {
    if (type.value.kind === "CONSTANT") type.value.value = value;
  });
}
function setSource(value: string): void {
  const selected = props.metadata.sources.find(
    (s) =>
      s.path === value &&
      s.fieldKinds.includes(props.field.typeDefinition.kind),
  );
  if (!selected) return;
  change((f) => {
    const settings = f.typeDefinition;
    if ("source" in settings.value)
      settings.value.source.path = selected.path as SourcePath;
    if ((settings.kind === "string" || settings.kind === "text") && !selected.requiresLocale) {
      settings.locale = null;
      settings.fallbackPolicy = null;
    }
  });
}
function fallbackMode(value: string): void {
  if (!["NONE", "LOCALE_CHAIN", "MANUAL_REQUIRED"].includes(value)) return;
  textChange((t) => {
    t.fallbackPolicy =
      value === "NONE" ? null : { mode: value as FallbackMode, locales: [] };
  });
}
function addFallback(value: string): void {
  textChange((t) => {
    if (
      t.fallbackPolicy &&
      value !== t.locale &&
      !t.fallbackPolicy.locales.includes(value)
    )
      t.fallbackPolicy.locales.push(value);
  });
}
function moveFallback(index: number, delta: number): void {
  textChange((t) => {
    const list = t.fallbackPolicy?.locales,
      next = index + delta;
    if (!list || next < 0 || next >= list.length) return;
    const [item] = list.splice(index, 1);
    list.splice(next, 0, item!);
  });
}
function changeScalar(value: ScalarTypeDraft): void {
  change((draft) => { draft.typeDefinition = value; });
}
function changeCategory(value: CategoryType, settings: SchemaFieldDraft["export"]): void {
  change((field) => { field.typeDefinition = value; field.export = settings; });
}
function message(key: string): string {
  return props.issues.find((i) => i.path.includes(key))?.message ?? "";
}
</script>
<template>
  <section class="flex min-w-0 flex-col gap-5" aria-label="Настройки поля">
    <header class="flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-lg font-semibold">Настройки поля</h2>
      <span class="text-sm text-muted-foreground">{{
        metadata.fieldTypes.find((t) => t.kind === field.typeDefinition.kind)?.label
      }}</span>
    </header>
    <Alert v-if="fieldIsReadonly(field)"
      ><AlertDescription
        >Формула использует пока неподключённые источники. Поле доступно для
        просмотра и сохраняется без изменений.</AlertDescription
      ></Alert
    >
    <FieldGroup>
      <FieldSet :disabled="locked">
        <FieldLegend>Поле и экспорт</FieldLegend>
        <FieldGroup>
          <Field :data-invalid="!!message('label')"
            ><FieldLabel for="schema-field-label">Подпись</FieldLabel
            ><Input
              id="schema-field-label"
              :model-value="field.label"
              :aria-invalid="!!message('label')"
              maxlength="255"
              @update:model-value="
                change((f) => {
                  f.label = String($event);
                })
              "
            /><FieldError v-if="message('label')">{{
              message("label")
            }}</FieldError></Field
          >
          <Field :data-invalid="!!message('key')"
            ><FieldLabel for="schema-field-key">Ключ</FieldLabel
            ><Input
              id="schema-field-key"
              :model-value="field.key"
              :aria-invalid="!!message('key')"
              maxlength="64"
              spellcheck="false"
              @update:model-value="
                change((f) => {
                  f.key = String($event);
                })
              "
            /><FieldDescription
              >Уникальный внутренний ключ. Переименование сохраняет
              идентификатор поля.</FieldDescription
            ><FieldError v-if="message('key')">{{
              message("key")
            }}</FieldError></Field
          >
          <Field :data-invalid="!!message('export')"
            ><FieldLabel for="schema-field-export-name">{{
              isXmlAttribute ? "Имя XML-атрибута" : xmlItemName ? "Имя XML-тега" : "Имя колонки"
            }}</FieldLabel><Input
              id="schema-field-export-name"
              :model-value="field.export.name"
              :aria-invalid="!!message('export')"
              maxlength="128"
              spellcheck="false"
              @update:model-value="
                change((f) => {
                  f.export.name = String($event);
                })
              "
            /><FieldDescription v-if="isXmlAttribute">
              <code class="break-all">{{ `<${xmlItemName} ${field.export.name.trim() || 'id'}="…">` }}</code>
            </FieldDescription><FieldError v-if="message('export')">{{
              message("export")
            }}</FieldError></Field
          >
          <Field v-if="xmlItemName && (!category || field.export.publication)" orientation="horizontal">
            <Checkbox
              id="schema-field-xml-attribute"
              :model-value="isXmlAttribute"
              :disabled="locked"
              @update:model-value="change((field) => {
                field.export.xmlPlacement = $event === true ? 'ATTRIBUTE' : 'ELEMENT';
              })"
            />
            <FieldLabel for="schema-field-xml-attribute">Выводить как атрибут предложения</FieldLabel>
          </Field>
          <Field orientation="horizontal"
            ><Checkbox
              id="schema-field-enabled"
              :model-value="field.export.enabled"
              :disabled="locked"
              @update:model-value="
                change((f) => {
                  f.export.enabled = $event === true;
                })
              "
            /><FieldLabel for="schema-field-enabled"
              >Включать в экспорт</FieldLabel
            ></Field
          >
        </FieldGroup>
      </FieldSet>
      <CategoryFieldSettings
        v-if="category"
        :value="category"
        :export-settings="field.export"
        :saved-ids="savedCategoryIds ?? []"
        :catalog="catalogCategories ?? []"
        :catalog-loading="catalogLoading ?? false"
        :catalog-error="catalogError ?? false"
        :locales="metadata.locales"
        :calculation-metadata="calculationMetadata"
        :disabled="locked"
        @change="changeCategory"
        @retry-catalog="emit('retryCatalog')"
      />
      <ScalarFieldSettings
        v-else-if="scalar"
        :value="scalar"
        :metadata="metadata"
        :calculation-metadata="calculationMetadata"
        :issues="issues"
        :disabled="locked"
        @change="changeScalar"
      />
      <template v-else-if="type">
      <FieldSet :disabled="locked">
        <FieldLegend>Получение значения</FieldLegend>
        <FieldGroup>
          <Field v-if="!fieldIsReadonly(field)"
            ><FieldLabel id="schema-value-mode-label"
              >Способ заполнения</FieldLabel
            ><ToggleGroup
              type="single"
              variant="outline"
              :model-value="mode"
              :disabled="locked"
              aria-labelledby="schema-value-mode-label"
              @update:model-value="setMode(String($event))"
              ><ToggleGroupItem
                v-for="valueMode in editableModes"
                :key="valueMode"
                :value="valueMode"
                :disabled="
                  locked || (valueMode === 'CALCULATED' && !calculationMetadata)
                "
                >{{
                  valueMode === "SOURCE"
                    ? "Источник"
                    : valueMode === "CALCULATED"
                      ? "Формула"
                      : valueMode === "CONSTANT"
                        ? "Заданное значение"
                        : "Вручную"
                }}</ToggleGroupItem
              ></ToggleGroup
            ></Field
          >
          <PriceCalculationForm
            v-if="
              type.kind === 'money' &&
              type.value.mode === 'CALCULATED' &&
              calculationMetadata &&
              !fieldIsReadonly(field)
            "
            :value="type.value.calculation"
            :metadata="calculationMetadata"
            :issues="issues"
            :disabled="locked"
            @change="
              moneyChange((t) => {
                if (t.value.mode === 'CALCULATED') t.value.calculation = $event;
              })
            "
          />
          <Field v-if="mode === 'MANUAL'"
            ><FieldDescription
              >Значение заполняется отдельно для товарного предложения. В схеме
              задаётся только способ получения.</FieldDescription
            ></Field
          >
          <Field
            v-if="type.kind !== 'money' && type.value.kind === 'CONSTANT'"
            :data-invalid="!!message('value')"
          >
            <FieldLabel for="schema-text-constant">Статический текст</FieldLabel>
            <Textarea
              v-if="type.kind === 'text'"
              id="schema-text-constant"
              :model-value="type.value.value"
              :aria-invalid="!!message('value')"
              rows="4"
              @update:model-value="setConstantValue(String($event))"
            />
            <Input
              v-else
              id="schema-text-constant"
              :model-value="type.value.value"
              :aria-invalid="!!message('value')"
              @update:model-value="setConstantValue(String($event))"
            />
            <FieldError v-if="message('value')">{{ message("value") }}</FieldError>
          </Field>
          <Field v-if="mode === 'SOURCE'" :data-invalid="!!message('source')"
            ><FieldLabel for="schema-field-source">Источник</FieldLabel
            ><Select
              :model-value="source || undefined"
              :disabled="locked"
              @update:model-value="setSource(String($event))"
              ><SelectTrigger
                id="schema-field-source"
                :aria-invalid="!!message('source')"
                ><SelectValue
                  placeholder="Выберите источник каталога" /></SelectTrigger
              ><SelectContent
                ><SelectGroup
                  ><SelectItem
                    v-for="item in sourceOptions"
                    :key="item.path"
                    :value="item.path"
                    >{{ item.label }}</SelectItem
                  ></SelectGroup
                ></SelectContent
              ></Select
            ><FieldError v-if="message('source')">{{
              message("source")
            }}</FieldError></Field
          >
          <template v-if="type.kind !== 'money' && localized">
            <Field :data-invalid="!!message('locale')"
              ><FieldLabel for="schema-field-locale">Локаль</FieldLabel
              ><Select
                :model-value="type.locale ?? 'none'"
                :disabled="locked"
                @update:model-value="
                  textChange((t) => {
                    t.locale = $event === 'none' ? null : String($event);
                    if (!t.locale) t.fallbackPolicy = null;
                    else if (t.fallbackPolicy)
                      t.fallbackPolicy.locales =
                        t.fallbackPolicy.locales.filter((l) => l !== t.locale);
                  })
                "
                ><SelectTrigger
                  id="schema-field-locale"
                  :aria-invalid="!!message('locale')"
                  ><SelectValue /></SelectTrigger
                ><SelectContent
                  ><SelectGroup
                    ><SelectItem value="none">Не задана</SelectItem
                    ><SelectItem
                      v-for="locale in metadata.locales"
                      :key="locale.code"
                      :value="locale.code"
                      >{{ locale.name }} ({{ locale.code }})</SelectItem
                    ><SelectItem
                      v-if="type.locale && currentLocaleUnavailable"
                      :value="type.locale"
                      >{{ type.locale }} — недоступна</SelectItem
                    ></SelectGroup
                  ></SelectContent
                ></Select
              ><FieldError v-if="message('locale')">{{
                message("locale")
              }}</FieldError></Field
            >
            <Field
              v-if="type.locale"
              :data-invalid="!!message('fallback_policy')"
              ><FieldLabel id="schema-fallback-label"
                >Если перевода нет</FieldLabel
              ><Select
                :model-value="type.fallbackPolicy?.mode ?? 'NONE'"
                :disabled="locked"
                @update:model-value="fallbackMode(String($event))"
                ><SelectTrigger aria-labelledby="schema-fallback-label"
                  ><SelectValue /></SelectTrigger
                ><SelectContent
                  ><SelectGroup
                    ><SelectItem value="NONE">Оставить без значения</SelectItem
                    ><SelectItem value="LOCALE_CHAIN"
                      >Использовать другие локали</SelectItem
                    ><SelectItem value="MANUAL_REQUIRED"
                      >Заполнить вручную</SelectItem
                    ></SelectGroup
                  ></SelectContent
                ></Select
              ><FieldError v-if="message('fallback_policy')">{{
                message("fallback_policy")
              }}</FieldError></Field
            >
            <Field v-if="type.fallbackPolicy?.mode === 'LOCALE_CHAIN'">
              <FieldLabel id="schema-fallback-locales-label"
                >Порядок запасных локалей</FieldLabel
              >
              <div
                v-for="(locale, index) in type.fallbackPolicy.locales"
                :key="locale"
                class="flex items-center gap-1"
              >
                <span class="flex-1 text-sm">{{ index + 1 }}. {{ locale }}</span
                ><Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  :disabled="locked || index === 0"
                  aria-label="Поднять локаль"
                  @click="moveFallback(index, -1)"
                  ><ArrowUp /></Button
                ><Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  :disabled="
                    locked || index === type.fallbackPolicy.locales.length - 1
                  "
                  aria-label="Опустить локаль"
                  @click="moveFallback(index, 1)"
                  ><ArrowDown /></Button
                ><Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  :disabled="locked"
                  aria-label="Убрать локаль"
                  @click="
                    textChange((t) => {
                      if (t.fallbackPolicy)
                        t.fallbackPolicy.locales =
                          t.fallbackPolicy.locales.filter((l) => l !== locale);
                    })
                  "
                  ><X
                /></Button>
              </div>
              <Select
                :model-value="''"
                :disabled="locked"
                @update:model-value="addFallback(String($event))"
                ><SelectTrigger aria-labelledby="schema-fallback-locales-label"
                  ><SelectValue placeholder="Добавить локаль" /></SelectTrigger
                ><SelectContent
                  ><SelectGroup
                    ><SelectItem
                      v-for="locale in fallbackOptions"
                      :key="locale.code"
                      :value="locale.code"
                      >{{ locale.name }} ({{ locale.code }})</SelectItem
                    ></SelectGroup
                  ></SelectContent
                ></Select
              >
            </Field>
          </template>
          <Field
            v-if="type.kind === 'money'"
            :data-invalid="!!message('currency')"
            ><FieldLabel for="schema-field-currency">Валютная метка</FieldLabel
            ><Input
              id="schema-field-currency"
              :model-value="type.currency ?? ''"
              :aria-invalid="!!message('currency')"
              maxlength="3"
              placeholder="Например, UAH"
              spellcheck="false"
              @update:model-value="
                moneyChange((t) => {
                  t.currency = String($event) || null;
                })
              "
            /><FieldDescription
              >Необязательный трёхбуквенный код. Пустое поле передаёт только
              сумму. Конвертация не выполняется.</FieldDescription
            ><FieldError v-if="message('currency')">{{
              message("currency")
            }}</FieldError></Field
          >
        </FieldGroup>
      </FieldSet>
      <FieldSet :disabled="locked">
        <FieldLegend>Ограничения</FieldLegend>
        <FieldGroup>
          <Field orientation="horizontal"
            ><Checkbox
              id="schema-field-required"
              :model-value="type.constraints.required"
              :disabled="locked"
              @update:model-value="
                change((f) => {
                  if (f.typeDefinition.kind !== 'category') f.typeDefinition.constraints.required = $event === true;
                })
              "
            /><FieldLabel for="schema-field-required"
              >Значение обязательно</FieldLabel
            ></Field
          >
          <FieldDescription
            >Обязательность значения не запрещает удалить поле из
            схемы.</FieldDescription
          >
          <template v-if="type.kind !== 'money'">
            <Field :data-invalid="!!message('constraints')"
              ><FieldLabel for="schema-field-min-length"
                >Минимальная длина</FieldLabel
              ><Input
                id="schema-field-min-length"
                :model-value="type.constraints.minLength"
                :aria-invalid="!!message('constraints')"
                inputmode="numeric"
                @update:model-value="
                  textChange((t) => {
                    t.constraints.minLength = String($event);
                  })
                "
            /></Field>
            <Field :data-invalid="!!message('constraints')"
              ><FieldLabel for="schema-field-max-length"
                >Максимальная длина</FieldLabel
              ><Input
                id="schema-field-max-length"
                :model-value="type.constraints.maxLength"
                :aria-invalid="!!message('constraints')"
                inputmode="numeric"
                @update:model-value="
                  textChange((t) => {
                    t.constraints.maxLength = String($event);
                  })
                "
            /></Field>
          </template>
          <template v-else>
            <Field :data-invalid="!!message('constraints')"
              ><FieldLabel for="schema-field-min-amount"
                >Минимальная сумма</FieldLabel
              ><Input
                id="schema-field-min-amount"
                :model-value="type.constraints.minAmount"
                :aria-invalid="!!message('constraints')"
                inputmode="decimal"
                @update:model-value="
                  moneyChange((t) => {
                    t.constraints.minAmount = String($event);
                  })
                "
            /></Field>
            <Field :data-invalid="!!message('constraints')"
              ><FieldLabel for="schema-field-max-amount"
                >Максимальная сумма</FieldLabel
              ><Input
                id="schema-field-max-amount"
                :model-value="type.constraints.maxAmount"
                :aria-invalid="!!message('constraints')"
                inputmode="decimal"
                @update:model-value="
                  moneyChange((t) => {
                    t.constraints.maxAmount = String($event);
                  })
                "
            /></Field>
          </template>
          <FieldError v-if="message('constraints')">{{
            message("constraints")
          }}</FieldError>
        </FieldGroup>
      </FieldSet>
      <SchemaTransformsForm
        :value="type.transforms"
        :kind="type.kind"
        :metadata="metadata"
        :disabled="locked"
        @change="
          change((f) => {
            const settings = f.typeDefinition;
            if (settings.kind !== 'integer' && settings.kind !== 'boolean' && settings.kind !== 'category')
              settings.transforms = $event;
          })
        "
      />
      <FieldError v-if="message('transforms')">{{
        message("transforms")
      }}</FieldError>
      </template>
    </FieldGroup>
  </section>
</template>
