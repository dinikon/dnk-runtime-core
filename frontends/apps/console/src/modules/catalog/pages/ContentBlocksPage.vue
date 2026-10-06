<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { toast } from "vue-sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { catalogApi } from "../api/catalog.api";
import type { ContentBlockType } from "../api/contracts";
import { catalogError } from "../model/forms";
import { useCatalogTenant, useContentBlocks, useLocales } from "../model/queries";
import RequestError from "../ui/RequestError.vue";

const tenant = useCatalogTenant();
const client = useQueryClient();
const definitions = useContentBlocks();
const locales = useLocales();
const selectedId = ref("");
const selected = computed(() => definitions.data.value?.find((item) => item.id === selectedId.value));
const code = ref("");
const type = ref<ContentBlockType>("text");
const translations = ref<Record<string, string>>({});
const addLocale = ref("");
const busy = ref(false);
const error = ref("");
watch(selected, (value) => {
  code.value = value?.code ?? "";
  type.value = value?.type ?? "text";
  translations.value = { ...(value?.translations ?? {}) };
}, { immediate: true });
function startNew() { selectedId.value = ""; code.value = ""; type.value = "text"; translations.value = {}; error.value = ""; }
async function refresh() { await client.invalidateQueries({ queryKey: ["catalog", tenant.value, "content-blocks"] }); }
async function save() {
  if (busy.value) return;
  busy.value = true; error.value = "";
  try {
    const names = Object.fromEntries(Object.entries(translations.value).map(([locale, name]) => [locale, name.trim()]).filter(([, name]) => name));
    const item = selected.value
      ? await catalogApi.putBlock(selected.value.id, { type: type.value, translations: names })
      : await catalogApi.createBlock({ code: code.value.trim(), type: type.value, translations: names });
    await refresh(); selectedId.value = item.id; toast.success("Определение сохранено");
  } catch (reason) { error.value = catalogError(reason); }
  finally { busy.value = false; }
}
async function remove() {
  if (!selected.value || selected.value.is_system || !window.confirm("Удалить определение блока?")) return;
  busy.value = true; error.value = "";
  try { await catalogApi.deleteBlock(selected.value.id); startNew(); await refresh(); toast.success("Определение удалено"); }
  catch (reason) { error.value = catalogError(reason); }
  finally { busy.value = false; }
}
function addTranslation() {
  if (addLocale.value && !(addLocale.value in translations.value)) translations.value = { ...translations.value, [addLocale.value]: "" };
  addLocale.value = "";
}
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex items-center justify-between"><div><h1 class="text-2xl font-semibold">Контент-блоки</h1><p class="text-sm text-muted-foreground">Переиспользуемые определения полей карточки</p></div><Button @click="startNew">Новый блок</Button></header>
    <RequestError v-if="definitions.isError.value" :message="catalogError(definitions.error.value)" retry @retry="definitions.refetch()" />
    <div class="grid gap-5 lg:grid-cols-[260px_minmax(0,1fr)]">
      <Card><CardHeader><CardTitle>Определения</CardTitle></CardHeader><CardContent class="space-y-1"><button v-for="item in definitions.data.value ?? []" :key="item.id" type="button" class="block w-full rounded-md px-3 py-2 text-left text-sm hover:bg-muted" :class="selectedId === item.id ? 'bg-muted font-medium' : ''" @click="selectedId = item.id">{{ item.code }} <span v-if="item.is_system" class="text-xs text-muted-foreground">· системный</span></button></CardContent></Card>
      <Card><CardHeader><CardTitle>{{ selected ? `Блок ${selected.code}` : "Новый блок" }}</CardTitle></CardHeader><CardContent class="space-y-4">
        <label class="block text-sm">Код<Input v-model="code" class="mt-1" :disabled="!!selected || busy" placeholder="ingredients" /></label>
        <label class="block text-sm">Тип<select v-model="type" class="mt-1 block h-9 w-full rounded-md border bg-background px-3" :disabled="selected?.is_system || busy"><option value="text">Текст</option><option value="rich_text">Форматированный текст</option></select></label>
        <div class="space-y-2"><h2 class="text-sm font-medium">Подписи</h2><div v-for="locale in Object.keys(translations).sort()" :key="locale" class="flex items-center gap-2"><span class="w-16 text-sm">{{ locale }}</span><Input v-model="translations[locale]" :disabled="busy" /><Button type="button" variant="outline" @click="delete translations[locale]">Убрать</Button></div><div class="flex gap-2"><select v-model="addLocale" class="h-9 flex-1 rounded-md border bg-background px-3 text-sm"><option value="">Добавить язык</option><option v-for="item in locales.data.value ?? []" :key="item.code" :value="item.code" :disabled="item.code in translations">{{ item.name }} · {{ item.code }}</option></select><Button type="button" variant="outline" @click="addTranslation">Добавить</Button></div></div>
        <RequestError v-if="error" :message="error" /><div class="flex gap-2"><Button :disabled="busy" @click="save">Сохранить</Button><Button v-if="selected && !selected.is_system" variant="destructive" :disabled="busy" @click="remove">Удалить</Button></div>
      </CardContent></Card>
    </div>
  </div>
</template>
