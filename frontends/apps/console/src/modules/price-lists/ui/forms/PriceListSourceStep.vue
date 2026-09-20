<script setup lang="ts">
import { ArrowRight, FileSearch, Loader2 } from "@lucide/vue";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { SourceFormat } from "../../model/types";

defineProps<{ busy: boolean; editMode: boolean; sourceUrlDisplay?: string }>();
defineEmits<{ submit: [] }>();

const title = defineModel<string>("title", { required: true });
const sourceUrl = defineModel<string>("sourceUrl", { required: true });
const sourceFormat = defineModel<SourceFormat>("sourceFormat", { required: true });
const preset = defineModel<"prom_xml" | "custom">("preset", { required: true });
const itemPath = defineModel<string>("itemPath", { required: true });
const sheetName = defineModel<string>("sheetName", { required: true });
const headerRow = defineModel<number>("headerRow", { required: true });
</script>

<template>
  <form class="flex flex-col gap-5" @submit.prevent="$emit('submit')">
    <Card>
      <CardHeader><CardTitle>Источник данных</CardTitle></CardHeader>
      <CardContent>
        <FieldGroup class="grid md:grid-cols-2">
          <Field class="md:col-span-2">
            <FieldLabel for="pl-title">Название</FieldLabel>
            <Input id="pl-title" v-model="title" required placeholder="Например, ProteinPlus закупка" />
          </Field>
          <Alert v-if="editMode && sourceUrlDisplay" class="md:col-span-2">
            <AlertDescription>Текущий защищённый URL: {{ sourceUrlDisplay }}</AlertDescription>
          </Alert>
          <Field class="md:col-span-2">
            <FieldLabel for="pl-url">{{ editMode ? "Новый HTTPS URL" : "HTTPS URL файла" }}</FieldLabel>
            <Input id="pl-url" v-model="sourceUrl" type="url" :required="!editMode" placeholder="https://partner.example/price.xlsx" />
            <FieldDescription v-if="editMode">Оставьте поле пустым, чтобы не менять текущий URL.</FieldDescription>
          </Field>
          <Field>
            <FieldLabel>Тип источника</FieldLabel>
            <Select v-model="preset">
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent><SelectGroup><SelectItem value="custom">Произвольный файл</SelectItem><SelectItem value="prom_xml">Prom XML</SelectItem></SelectGroup></SelectContent>
            </Select>
          </Field>
          <Field>
            <FieldLabel>Формат</FieldLabel>
            <Select v-model="sourceFormat" :disabled="preset === 'prom_xml'">
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent><SelectGroup><SelectItem value="xml">XML</SelectItem><SelectItem value="yaml">YAML</SelectItem><SelectItem value="xlsx">XLSX</SelectItem></SelectGroup></SelectContent>
            </Select>
          </Field>
          <template v-if="sourceFormat === 'xlsx'">
            <Field><FieldLabel for="sheet-name">Лист</FieldLabel><Input id="sheet-name" v-model="sheetName" /></Field>
            <Field><FieldLabel for="header-row">Строка заголовков</FieldLabel><Input id="header-row" v-model.number="headerRow" type="number" min="1" /></Field>
          </template>
          <Field v-else class="md:col-span-2">
            <FieldLabel for="item-path">Путь к элементам</FieldLabel>
            <Input id="item-path" v-model="itemPath" :required="preset === 'custom'" placeholder="root.shop.offers.offer" />
          </Field>
        </FieldGroup>
      </CardContent>
    </Card>
    <div class="flex justify-end">
      <Button type="submit" :disabled="busy"><Loader2 v-if="busy" data-icon="inline-start" class="animate-spin" /><FileSearch v-else data-icon="inline-start" />Предзагрузить<ArrowRight data-icon="inline-end" /></Button>
    </div>
  </form>
</template>
