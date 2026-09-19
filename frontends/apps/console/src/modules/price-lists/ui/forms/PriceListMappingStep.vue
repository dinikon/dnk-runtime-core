<script setup lang="ts">
import { ArrowLeft, ArrowRight, Check } from "@lucide/vue";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { MappingConfig, PreviewResult } from "../../model/types";

defineProps<{
  preview: PreviewResult | null;
  mapping: MappingConfig;
  fields: readonly { key: string; label: string; required: boolean }[];
  availableSelectors: string[];
  mappingComplete: boolean;
  busy: boolean;
}>();
defineEmits<{ back: []; submit: []; setSelector: [key: string, value: unknown] }>();
</script>

<template>
  <form class="flex min-h-0 flex-col gap-4" @submit.prevent="$emit('submit')">
    <div class="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(340px,1fr)]">
      <Card>
        <CardHeader><CardTitle>Предпросмотр источника</CardTitle></CardHeader>
        <CardContent class="overflow-auto">
          <Table v-if="preview?.rows.length">
            <TableHeader><TableRow><TableHead v-for="key in Object.keys(preview.rows[0]?.values ?? {})" :key="key">{{ key }}</TableHead></TableRow></TableHeader>
            <TableBody><TableRow v-for="row in preview.rows.slice(0, 8)" :key="row.row_number"><TableCell v-for="key in Object.keys(preview.rows[0]?.values ?? {})" :key="key">{{ row.values[key] ?? '—' }}</TableCell></TableRow></TableBody>
          </Table>
          <div v-else class="min-h-48">
            <p class="text-sm text-muted-foreground">Найдены поля источника:</p>
            <div class="mt-3 flex flex-wrap gap-2"><span v-for="column in availableSelectors" :key="column" class="rounded-md border bg-muted/40 px-2 py-1 text-sm">{{ column }}</span><span v-if="!availableSelectors.length" class="text-sm text-muted-foreground">Для XML/YAML введите селекторы вручную.</span></div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Сопоставление полей</CardTitle></CardHeader>
        <CardContent>
          <FieldGroup>
            <Field v-for="field in fields" :key="field.key">
              <FieldLabel :for="`mapping-${field.key}`">{{ field.label }}<span v-if="field.required" class="text-destructive"> *</span></FieldLabel>
              <Select v-if="availableSelectors.length" :model-value="mapping[field.key]?.selector" @update:model-value="$emit('setSelector', field.key, $event)">
                <SelectTrigger :id="`mapping-${field.key}`"><SelectValue placeholder="Выберите колонку" /></SelectTrigger>
                <SelectContent><SelectGroup><SelectItem v-for="column in availableSelectors" :key="column" :value="column">{{ column }}</SelectItem></SelectGroup></SelectContent>
              </Select>
              <Input v-else :id="`mapping-${field.key}`" :model-value="mapping[field.key]?.selector ?? ''" placeholder="Селектор или @атрибут" @update:model-value="$emit('setSelector', field.key, $event)" />
            </Field>
          </FieldGroup>
          <Alert class="mt-4"><Check /><AlertDescription>{{ mappingComplete ? 'Все обязательные поля сопоставлены' : 'Заполните обязательные поля' }}</AlertDescription></Alert>
        </CardContent>
      </Card>
    </div>
    <div class="flex justify-between"><Button type="button" variant="outline" @click="$emit('back')"><ArrowLeft data-icon="inline-start" />Назад</Button><Button type="submit" :disabled="busy || !mappingComplete">Проверить и продолжить<ArrowRight data-icon="inline-end" /></Button></div>
  </form>
</template>
