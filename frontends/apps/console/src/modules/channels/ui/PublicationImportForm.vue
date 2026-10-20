<script setup lang="ts">
import { computed, ref } from "vue";
import { CatalogContentEditor } from "@/modules/catalog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type {
  ImportDraftValues,
  PublicationImportImage,
} from "../model/publication-import.types";
import type { ConnectionReferences } from "../model/channels.types";
import { confirmedDraft, draftFormIssue } from "../model/draft-form";
import { copyImportValues } from "../model/publication-import-draft";
import PublicationImportGallery from "./PublicationImportGallery.vue";
const props = defineProps<{
  values: ImportDraftValues;
  images: readonly PublicationImportImage[];
  references: ConnectionReferences | undefined;
  disabled: boolean;
  pending: boolean;
  locale: string;
}>();
const emit = defineEmits<{
  "update:values": [value: ImportDraftValues];
  submit: [value: ImportDraftValues];
  locale: [value: string];
}>();
const locales = computed(() => Object.keys(props.values.titles));
const activeLocale = computed({
  get: () => props.locale,
  set: (value: string | number) => emit("locale", String(value)),
});
const includePrices = computed(
    () => props.values.copyPrices ?? props.values.regularPrice !== null,
  ),
  localError = ref<string | null>(null);
const unavailable = computed(() =>
  props.values.gallery.some(
    (id) => !props.images.find((image) => image.id === id)?.previewUrl,
  ),
);
function patch(values: Partial<ImportDraftValues>): void {
  emit("update:values", { ...copyImportValues(props.values), ...values });
}
function title(locale: string, value: string | number): void {
  patch({ titles: { ...props.values.titles, [locale]: String(value) } });
}
function body(locale: string, value: string): void {
  patch({ descriptions: { ...props.values.descriptions, [locale]: value } });
}
function submit(): void {
  const values = confirmedDraft(
    props.values,
    includePrices.value,
  ) as ImportDraftValues;
  localError.value = draftFormIssue(values);
  if (!localError.value && !unavailable.value && !props.disabled)
    emit("submit", values);
}
</script>
<template>
  <form class="flex min-w-0 flex-col gap-6" @submit.prevent="submit">
    <Card
      ><CardHeader
        ><CardTitle>Название и описание</CardTitle
        ><CardDescription
          >Языки взяты из настроек подключения. Проверьте полученный текст перед
          созданием.</CardDescription
        ></CardHeader
      ><CardContent>
        <Tabs v-model="activeLocale"
          ><TabsList class="mb-4"
            ><TabsTrigger
              v-for="locale in locales"
              :key="locale"
              :value="locale"
              >{{ locale.toUpperCase() }}</TabsTrigger
            ></TabsList
          >
          <TabsContent v-for="locale in locales" :key="locale" :value="locale"
            ><FieldGroup>
              <Field
                ><FieldLabel :for="`import-title-${locale}`"
                  >Название · {{ locale }}</FieldLabel
                ><Input
                  :id="`import-title-${locale}`"
                  :model-value="values.titles[locale]"
                  :disabled="disabled"
                  maxlength="255"
                  required
                  @update:model-value="(value) => title(locale, value)"
              /></Field>
              <Field
                ><FieldLabel>Описание · {{ locale }}</FieldLabel
                ><CatalogContentEditor
                  :model-value="values.descriptions[locale] ?? ''"
                  :disabled="disabled"
                  :label="`Описание · ${locale}`"
                  @update:model-value="(value) => body(locale, value)"
                /><FieldDescription v-if="!values.descriptions[locale]"
                  >Источник не передал описание на этом языке. Его можно
                  заполнить здесь.</FieldDescription
                ></Field
              >
            </FieldGroup></TabsContent
          >
        </Tabs>
      </CardContent></Card
    >
    <PublicationImportGallery
      :values="values"
      :images="images"
      :disabled="disabled"
      @update:values="(value) => emit('update:values', value)"
    />
    <Card
      ><CardHeader
        ><CardTitle>Цена и наличие</CardTitle
        ><CardDescription
          >Будут сохранены как исходные значения нового товара.</CardDescription
        ></CardHeader
      ><CardContent
        ><FieldGroup>
          <Field
            ><FieldLabel for="import-sku">SKU товара</FieldLabel
            ><Input
              id="import-sku"
              :model-value="values.sku ?? ''"
              :disabled="disabled"
              maxlength="128"
              @update:model-value="
                (value) => patch({ sku: String(value) || null })
              "
          /></Field>
          <Field
            ><FieldLabel for="import-prices">Перенос цен</FieldLabel
            ><NativeSelect
              id="import-prices"
              :model-value="includePrices ? 'copy' : 'skip'"
              :disabled="disabled"
              @update:model-value="
                (value) => patch({ copyPrices: value === 'copy' })
              "
              ><NativeSelectOption value="copy"
                >Перенести цены</NativeSelectOption
              ><NativeSelectOption value="skip"
                >Создать без цен</NativeSelectOption
              ></NativeSelect
            ></Field
          >
          <div v-if="includePrices" class="grid gap-4 sm:grid-cols-3">
            <Field
              ><FieldLabel for="import-price">Базовая цена</FieldLabel
              ><Input
                id="import-price"
                :model-value="values.regularPrice ?? ''"
                :disabled="disabled"
                inputmode="decimal"
                required
                @update:model-value="
                  (value) => patch({ regularPrice: String(value) })
                "
            /></Field>
            <Field
              ><FieldLabel for="import-sale">Акционная цена</FieldLabel
              ><Input
                id="import-sale"
                :model-value="values.salePrice ?? ''"
                :disabled="disabled"
                inputmode="decimal"
                @update:model-value="
                  (value) => patch({ salePrice: String(value) || null })
                "
            /></Field>
            <Field
              ><FieldLabel for="import-currency">Валюта</FieldLabel
              ><NativeSelect
                id="import-currency"
                :model-value="values.currency ?? ''"
                :disabled="disabled"
                @update:model-value="
                  (value) => patch({ currency: String(value) || null })
                "
                ><NativeSelectOption value=""
                  >Выберите валюту</NativeSelectOption
                ><NativeSelectOption
                  v-for="currency in references?.currencies ?? []"
                  :key="currency.code"
                  :value="currency.code"
                  >{{ currency.code }}</NativeSelectOption
                ></NativeSelect
              ></Field
            >
          </div>
          <Field
            ><FieldLabel for="import-stock">Учёт наличия</FieldLabel
            ><NativeSelect
              id="import-stock"
              :model-value="values.manageStock ? 'quantity' : 'manual'"
              :disabled="disabled"
              @update:model-value="
                (value) => patch({ manageStock: value === 'quantity' })
              "
              ><NativeSelectOption value="quantity"
                >По количеству</NativeSelectOption
              ><NativeSelectOption value="manual"
                >Ручной статус</NativeSelectOption
              ></NativeSelect
            ></Field
          >
          <template v-if="values.manageStock">
            <Field
              ><FieldLabel for="import-quantity">Количество</FieldLabel
              ><Input
                id="import-quantity"
                :model-value="values.quantity ?? ''"
                :disabled="disabled"
                inputmode="numeric"
                required
                @update:model-value="
                  (value) => patch({ quantity: String(value) })
                "
              /><FieldDescription
                >Статус наличия вычисляется по количеству и разрешению
                предзаказа.</FieldDescription
              ></Field
            >
            <Field
              ><FieldLabel for="import-backorders"
                >Предзаказ при нулевом остатке</FieldLabel
              ><NativeSelect
                id="import-backorders"
                :model-value="values.backorders"
                :disabled="disabled"
                @update:model-value="
                  (value) => patch({ backorders: String(value) })
                "
                ><NativeSelectOption value="no">Запрещён</NativeSelectOption
                ><NativeSelectOption value="notify"
                  >Разрешён с уведомлением</NativeSelectOption
                ><NativeSelectOption value="yes"
                  >Разрешён</NativeSelectOption
                ></NativeSelect
              ></Field
            >
          </template>
          <Field v-else
            ><FieldLabel for="import-presence">Наличие</FieldLabel
            ><NativeSelect
              id="import-presence"
              :model-value="values.stockStatus ?? ''"
              :disabled="disabled"
              @update:model-value="
                (value) => patch({ stockStatus: String(value) || null })
              "
              ><NativeSelectOption value="">Выберите статус</NativeSelectOption
              ><NativeSelectOption value="in_stock"
                >В наличии</NativeSelectOption
              ><NativeSelectOption value="out_of_stock"
                >Нет в наличии</NativeSelectOption
              ><NativeSelectOption value="on_backorder"
                >Под заказ</NativeSelectOption
              ></NativeSelect
            ></Field
          >
        </FieldGroup></CardContent
      ></Card
    >
    <Alert v-if="localError || unavailable"
      ><AlertDescription>{{
        localError ??
        "Часть фотографий ещё не готова. Повторите перенос или явно исключите их из галереи."
      }}</AlertDescription></Alert
    >
    <div class="flex flex-wrap justify-end gap-3">
      <Button type="submit" :disabled="disabled || unavailable">{{
        pending ? "Создаём товар…" : "Создать Draft"
      }}</Button>
    </div>
  </form>
</template>
