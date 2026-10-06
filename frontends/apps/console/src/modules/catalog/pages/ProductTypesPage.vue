<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { catalogApi } from "../api/catalog.api";
import type { ContentScope, TypeBlockPayload } from "../api/contracts";
import { catalogError } from "../model/forms";
import { useCatalogTenant, useContentBlocks, useLocales, useProductTypes } from "../model/queries";
import RequestError from "../ui/RequestError.vue";

const tenant = useCatalogTenant();
const client = useQueryClient();
const types = useProductTypes();
const definitions = useContentBlocks();
const locales = useLocales();
const selectedId = ref("");
const selected = computed(() => types.data.value?.find((item) => item.id === selectedId.value));
const code = ref("");
const translations = ref<Record<string, string>>({});
const blocks = ref<TypeBlockPayload[]>([]);
const addLocale = ref("");
const addProductBlock = ref("");
const addVariantBlock = ref("");
const busy = ref(false);
const error = ref("");
watch(selected, (value) => {
  code.value = value?.code ?? "";
  translations.value = { ...(value?.translations ?? {}) };
  blocks.value = value?.blocks.map(({ block_id, scope, required, position }) => ({ block_id, scope, required, position })) ?? [];
}, { immediate: true });
function startNew() { selectedId.value = ""; code.value = ""; translations.value = {}; blocks.value = []; error.value = ""; }
function scoped(scope: ContentScope) { return blocks.value.filter((item) => item.scope === scope).sort((a, b) => a.position - b.position); }
function label(blockId: string) { const item = definitions.data.value?.find((block) => block.id === blockId); return item ? `${item.code} · ${item.type}` : blockId; }
function normalize(scope: ContentScope, items: TypeBlockPayload[]) {
  blocks.value = [...blocks.value.filter((item) => item.scope !== scope), ...items.map((item, position) => ({ ...item, position }))];
}
function add(scope: ContentScope) {
  const blockId = scope === "product" ? addProductBlock.value : addVariantBlock.value;
  if (!blockId || scoped(scope).some((item) => item.block_id === blockId)) return;
  normalize(scope, [...scoped(scope), { block_id: blockId, scope, required: false, position: 0 }]);
  if (scope === "product") addProductBlock.value = ""; else addVariantBlock.value = "";
}
function remove(scope: ContentScope, blockId: string) { normalize(scope, scoped(scope).filter((item) => item.block_id !== blockId)); }
function move(scope: ContentScope, index: number, step: number) {
  const items = scoped(scope); const target = index + step;
  if (target < 0 || target >= items.length) return;
  [items[index], items[target]] = [items[target]!, items[index]!]; normalize(scope, items);
}
function addTranslation() {
  if (addLocale.value && !(addLocale.value in translations.value)) translations.value = { ...translations.value, [addLocale.value]: "" };
  addLocale.value = "";
}
async function refresh() { await client.invalidateQueries({ queryKey: ["catalog", tenant.value, "product-types"] }); }
async function save() {
  if (busy.value) return; busy.value = true; error.value = "";
  try {
    const names = Object.fromEntries(Object.entries(translations.value).map(([locale, name]) => [locale, name.trim()]).filter(([, name]) => name));
    const item = selected.value
      ? await catalogApi.putProductTypeSchema(selected.value.id, { expected_schema_version: selected.value.schema_version, translations: names, blocks: blocks.value })
      : await catalogApi.createProductType({ code: code.value.trim(), translations: names, blocks: blocks.value });
    await refresh(); selectedId.value = item.id; toast.success("Тип товара сохранён");
  } catch (reason) { error.value = catalogError(reason); }
  finally { busy.value = false; }
}
async function removeType() {
  if (!selected.value || selected.value.is_system || !window.confirm("Удалить тип товара?")) return;
  busy.value = true; error.value = "";
  try { await catalogApi.deleteProductType(selected.value.id); startNew(); await refresh(); toast.success("Тип товара удалён"); }
  catch (reason) { error.value = catalogError(reason); }
  finally { busy.value = false; }
}
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex items-center justify-between"><div><h1 class="text-2xl font-semibold">Типы товаров</h1><p class="text-sm text-muted-foreground">Схема контента товара и его вариантов</p></div><Button @click="startNew">Новый тип</Button></header>
    <RequestError v-if="types.isError.value" :message="catalogError(types.error.value)" retry @retry="types.refetch()" />
    <div class="grid gap-5 lg:grid-cols-[260px_minmax(0,1fr)]">
      <Card><CardHeader><CardTitle>Шаблоны</CardTitle></CardHeader><CardContent class="space-y-1"><button v-for="item in types.data.value ?? []" :key="item.id" type="button" class="block w-full rounded-md px-3 py-2 text-left text-sm hover:bg-muted" :class="selectedId === item.id ? 'bg-muted font-medium' : ''" @click="selectedId = item.id">{{ item.translations.ru ?? item.code }} <span v-if="item.is_system" class="text-xs text-muted-foreground">· системный</span></button></CardContent></Card>
      <Card><CardHeader><CardTitle>{{ selected ? `Тип ${selected.code}` : "Новый тип" }}</CardTitle></CardHeader><CardContent class="space-y-6">
        <label class="block text-sm">Код<Input v-model="code" class="mt-1" :disabled="!!selected || busy" placeholder="vitamins" /></label>
        <div class="space-y-2"><h2 class="text-sm font-medium">Названия</h2><div v-for="locale in Object.keys(translations).sort()" :key="locale" class="flex items-center gap-2"><span class="w-16 text-sm">{{ locale }}</span><Input v-model="translations[locale]" :disabled="busy" /><Button type="button" variant="outline" @click="delete translations[locale]">Убрать</Button></div><div class="flex gap-2"><select v-model="addLocale" class="h-9 flex-1 rounded-md border bg-background px-3 text-sm"><option value="">Добавить язык</option><option v-for="item in locales.data.value ?? []" :key="item.code" :value="item.code" :disabled="item.code in translations">{{ item.name }} · {{ item.code }}</option></select><Button type="button" variant="outline" @click="addTranslation">Добавить</Button></div></div>
        <section v-for="scope in (['product', 'variant'] as const)" :key="scope" class="space-y-3 rounded-lg border p-4"><h2 class="font-medium">{{ scope === 'product' ? 'PRODUCT · карточка' : 'VARIANT · вариант' }}</h2><div v-for="(item, index) in scoped(scope)" :key="item.block_id" class="flex flex-wrap items-center gap-2 rounded-md bg-muted/40 p-2 text-sm"><span class="min-w-40 flex-1">{{ label(item.block_id) }}</span><label class="flex items-center gap-1"><input v-model="item.required" type="checkbox" :disabled="selected?.is_system || busy" />Обязателен</label><Button type="button" size="sm" variant="outline" :disabled="index === 0 || selected?.is_system" @click="move(scope, index, -1)">↑</Button><Button type="button" size="sm" variant="outline" :disabled="index === scoped(scope).length - 1 || selected?.is_system" @click="move(scope, index, 1)">↓</Button><Button v-if="!selected?.is_system" type="button" size="sm" variant="outline" @click="remove(scope, item.block_id)">Убрать</Button></div><div v-if="!selected?.is_system" class="flex gap-2"><select :value="scope === 'product' ? addProductBlock : addVariantBlock" class="h-9 flex-1 rounded-md border bg-background px-3 text-sm" @change="scope === 'product' ? addProductBlock = ($event.target as HTMLSelectElement).value : addVariantBlock = ($event.target as HTMLSelectElement).value"><option value="">Выберите блок</option><option v-for="item in definitions.data.value ?? []" :key="item.id" :value="item.id" :disabled="scoped(scope).some((value) => value.block_id === item.id)">{{ item.code }}</option></select><Button type="button" variant="outline" @click="add(scope)">Добавить</Button></div></section>
        <RequestError v-if="error" :message="error" /><div class="flex gap-2"><Button :disabled="busy" @click="save">Сохранить</Button><Button v-if="selected && !selected.is_system" variant="destructive" :disabled="busy" @click="removeType">Удалить</Button></div>
      </CardContent></Card>
    </div>
  </div>
</template>
