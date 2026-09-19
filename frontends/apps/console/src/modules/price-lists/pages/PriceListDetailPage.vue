<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Archive, Pencil, Pause, Play, RefreshCw, RotateCcw, Trash2 } from "@lucide/vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePriceListAction } from "../model/use-price-list-action";
import { useDeletePriceList } from "../model/use-delete-price-list";
import { usePriceListQuery } from "../model/use-price-list-query";
import { usePriceListRunsQuery } from "../model/use-price-list-runs-query";
import DeletePriceListConfirmDialog from "../ui/management/DeletePriceListConfirmDialog.vue";

const route = useRoute();
const router = useRouter();
const id = computed(() => String(route.params.id));
type DetailTab = "overview" | "offers" | "runs" | "settings";
const tab = computed<DetailTab>({
  get: () => {
    const value = String(route.query.tab ?? "overview");
    return ["overview", "offers", "runs", "settings"].includes(value)
      ? value as DetailTab
      : "overview";
  },
  set: (value) => { void router.replace({ query: { ...route.query, tab: value } }); },
});
const detail = usePriceListQuery(id);
const runs = usePriceListRunsQuery(id);
const action = usePriceListAction();
const deleteMutation = useDeletePriceList();
const deleteOpen = ref(false);
async function deletePriceList(confirmationTitle: string) {
  await deleteMutation.mutateAsync({ id: id.value, confirmationTitle });
  deleteOpen.value = false;
  await router.push({ name: "price-lists" });
}
</script>

<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <div v-if="detail.isPending.value" class="text-sm text-muted-foreground">Загрузка прайс-листа…</div>
    <template v-else-if="detail.data.value">
      <header class="flex flex-wrap items-end justify-between gap-3"><div><p class="text-sm text-muted-foreground">Закупки / Прайс-листы</p><div class="flex items-center gap-2"><h1 class="text-2xl font-semibold tracking-tight">{{ detail.data.value.title }}</h1><Badge variant="outline">{{ detail.data.value.status }}</Badge></div><p class="mt-1 text-sm text-muted-foreground">{{ detail.data.value.source_url_display }}</p></div><div class="flex flex-wrap gap-2"><Button v-if="detail.data.value.status === 'active'" variant="outline" disabled title="Сначала поставьте прайс-лист на паузу"><Pencil data-icon="inline-start" />Настройки</Button><Button v-else-if="detail.data.value.status !== 'archived'" variant="outline" as-child><RouterLink :to="`/purchases/price-lists/${id}/edit`"><Pencil data-icon="inline-start" />Настройки</RouterLink></Button><Button v-if="detail.data.value.status === 'active'" variant="outline" :disabled="action.isPending.value" @click="action.mutate({ id, action: 'sync' })"><RefreshCw data-icon="inline-start" />Загрузить сейчас</Button><Button v-if="detail.data.value.status === 'active'" variant="outline" @click="action.mutate({ id, action: 'pause' })"><Pause data-icon="inline-start" />Пауза</Button><Button v-if="detail.data.value.status === 'paused'" @click="action.mutate({ id, action: 'resume' })"><Play data-icon="inline-start" />Возобновить</Button><Button v-if="detail.data.value.status === 'archived'" @click="action.mutate({ id, action: 'restore' })"><RotateCcw data-icon="inline-start" />Восстановить</Button></div></header>
      <div class="grid gap-3 md:grid-cols-3"><Card><CardHeader><CardTitle class="text-sm">Формат</CardTitle></CardHeader><CardContent class="text-xl font-semibold uppercase">{{ detail.data.value.source_format }}</CardContent></Card><Card><CardHeader><CardTitle class="text-sm">Расписание</CardTitle></CardHeader><CardContent><div class="font-semibold">{{ detail.data.value.cron_expression ?? 'Не задано' }}</div><div class="text-xs text-muted-foreground">{{ detail.data.value.timezone }}</div></CardContent></Card><Card><CardHeader><CardTitle class="text-sm">Последняя загрузка</CardTitle></CardHeader><CardContent>{{ detail.data.value.last_success_at ? new Date(detail.data.value.last_success_at).toLocaleString('uk-UA') : 'Ожидается первая загрузка' }}</CardContent></Card></div>
      <Tabs v-model="tab"><TabsList><TabsTrigger value="overview">Обзор</TabsTrigger><TabsTrigger value="offers">Офферы</TabsTrigger><TabsTrigger value="runs">Запуски</TabsTrigger><TabsTrigger value="settings">Настройки</TabsTrigger></TabsList><TabsContent value="overview"><Card><CardContent class="grid gap-2 py-6 text-sm"><p>Прайс-лист отслеживает закупочную цену, РРЦ и наличие предложений партнёра.</p><p class="text-muted-foreground">Следующая загрузка: {{ detail.data.value.next_sync_at ? new Date(detail.data.value.next_sync_at).toLocaleString('uk-UA') : 'не запланирована' }}</p></CardContent></Card></TabsContent><TabsContent value="offers"><Card><CardContent class="flex items-center justify-between gap-3 py-6"><p class="text-sm text-muted-foreground">Откройте общую таблицу с зафиксированным фильтром этого прайс-листа.</p><Button as-child><RouterLink :to="{ name: 'partner-offers', query: { price_list_id: id, ...(detail.data.value.status === 'archived' ? { include_archived: 'true' } : {}) } }">Открыть офферы</RouterLink></Button></CardContent></Card></TabsContent><TabsContent value="runs" class="rounded-lg border"><Table><TableHeader><TableRow><TableHead>Начало</TableHead><TableHead>Триггер</TableHead><TableHead>Статус</TableHead><TableHead>Прочитано</TableHead><TableHead>Изменено</TableHead><TableHead>Ошибка</TableHead></TableRow></TableHeader><TableBody><TableRow v-if="!runs.data.value?.length"><TableCell colspan="6" class="h-32 text-center text-muted-foreground">Запусков пока нет.</TableCell></TableRow><TableRow v-for="run in runs.data.value ?? []" :key="run.id"><TableCell>{{ new Date(run.started_at).toLocaleString('uk-UA') }}</TableCell><TableCell>{{ run.trigger }}</TableCell><TableCell><Badge :variant="run.status === 'succeeded' ? 'secondary' : 'outline'">{{ run.status }}</Badge></TableCell><TableCell>{{ run.counters.read ?? '—' }}</TableCell><TableCell>{{ run.counters.changed ?? '—' }}</TableCell><TableCell class="text-destructive">{{ run.error_summary ?? '—' }}</TableCell></TableRow></TableBody></Table></TabsContent><TabsContent value="settings" class="flex flex-col gap-4"><Card><CardHeader><CardTitle>Конфигурация</CardTitle></CardHeader><CardContent class="grid gap-3 text-sm"><div><span class="text-muted-foreground">Путь / лист:</span> {{ detail.data.value.source_config }}</div><div><span class="text-muted-foreground">Следующий запуск:</span> {{ detail.data.value.next_sync_at ? new Date(detail.data.value.next_sync_at).toLocaleString('uk-UA') : '—' }}</div></CardContent></Card><Card><CardHeader><CardTitle>Опасная зона</CardTitle></CardHeader><CardContent class="flex flex-wrap items-center justify-between gap-3"><p class="text-sm text-muted-foreground">Архив сохраняет историю. Окончательное удаление стирает её безвозвратно.</p><Button v-if="detail.data.value.status !== 'archived'" variant="outline" @click="action.mutate({ id, action: 'archive' })"><Archive data-icon="inline-start" />Архивировать</Button><Button v-else variant="destructive" @click="deleteOpen = true"><Trash2 data-icon="inline-start" />Удалить окончательно</Button></CardContent></Card></TabsContent></Tabs>
      <DeletePriceListConfirmDialog :open="deleteOpen" :price-list="detail.data.value" :pending="deleteMutation.isPending.value" @update:open="deleteOpen = $event" @confirm="deletePriceList" />
    </template>
  </div>
</template>
