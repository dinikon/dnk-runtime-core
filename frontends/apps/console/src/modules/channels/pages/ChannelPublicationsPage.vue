<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
  EmptyContent,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableHeader,
  TableHead,
  TableRow,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import { channelsApi } from "../api/channels.api";
import {
  useChannel,
  useChannelTenant,
  usePublicationImport,
  usePublications,
} from "../model/queries";
import {
  importLabels,
  importError,
  sourceLabel,
  priceLabel,
  dateLabel,
} from "../model/publications";
const route = useRoute(),
  client = useQueryClient();
const id = computed(() => String(route.params.channelId ?? ""));
const tenant = useChannelTenant(),
  offset = ref(0),
  pending = ref(false),
  error = ref("");
const channel = useChannel(id),
  run = usePublicationImport(id),
  publications = usePublications(id, offset);
const active = computed(() =>
  ["queued", "running"].includes(run.data.value?.status ?? ""),
);
const supported = computed(() =>
  ["prom", "woocommerce"].includes(channel.data.value?.kind ?? ""),
);
let generation = 0,
  operation: AbortController | null = null;
function reset() {
  generation++;
  operation?.abort();
  pending.value = false;
  offset.value = 0;
  error.value = "";
}
watch([tenant, id], reset);
onBeforeUnmount(reset);
async function refresh() {
  if (pending.value || active.value) return;
  const current = generation,
    requestTenant = tenant.value,
    requestId = id.value;
  pending.value = true;
  error.value = "";
  operation = new AbortController();
  try {
    await channelsApi.startImport(requestId, operation.signal);
    if (current !== generation) return;
    await client.invalidateQueries({
      queryKey: ["channels", requestTenant, "imports", requestId],
    });
  } catch (reason) {
    if (current === generation)
      error.value =
        reason instanceof Error
          ? reason.message
          : "Не удалось загрузить публикации.";
  } finally {
    if (current === generation) pending.value = false;
  }
}
</script>
<template>
  <div class="flex flex-col gap-4">
    <Card>
      <CardHeader
        class="flex flex-wrap items-start justify-between gap-3 sm:flex-row"
      >
        <div class="flex flex-col gap-1.5">
          <CardTitle>Публикации</CardTitle
          ><CardDescription
            >Сохранённые карточки из внешнего магазина.</CardDescription
          >
        </div>
        <Button
          v-if="supported"
          :disabled="pending || active || !channel.data.value?.is_active"
          @click="refresh"
          >{{
            pending
              ? "Запуск…"
              : active
                ? "Загрузка…"
                : run.data.value
                  ? "Обновить публикации"
                  : "Загрузить публикации"
          }}</Button
        >
      </CardHeader>
      <CardContent class="flex flex-col gap-4">
        <Alert v-if="!supported"
          ><AlertTitle>Чтение публикаций пока недоступно</AlertTitle
          ><AlertDescription
            >В этом срезе поддерживаются Prom и WooCommerce.</AlertDescription
          ></Alert
        >
        <Alert v-else-if="!channel.data.value?.is_active"
          ><AlertTitle>Канал выключен</AlertTitle
          ><AlertDescription
            >Включите канал в настройках подключения, чтобы загрузить
            публикации.</AlertDescription
          ></Alert
        >
        <Alert
          v-if="run.data.value"
          :variant="run.data.value.error_code ? 'destructive' : 'default'"
          role="status"
        >
          <AlertTitle>{{ importLabels[run.data.value.status] }}</AlertTitle>
          <AlertDescription
            >Ресурсов: {{ run.data.value.resources }} · Страниц:
            {{ run.data.value.pages
            }}<span v-if="run.data.value.error_code"
              >. {{ importError(run.data.value.error_code) }}</span
            ></AlertDescription
          >
        </Alert>
        <Alert v-if="error || run.isError.value" variant="destructive"
          ><AlertTitle>{{
            error || "Не удалось получить состояние загрузки"
          }}</AlertTitle
          ><AlertDescription
            ><Button
              v-if="run.isError.value"
              variant="outline"
              @click="run.refetch()"
              >Повторить</Button
            ></AlertDescription
          ></Alert
        >
        <Alert v-if="publications.isError.value" variant="destructive"
          ><AlertTitle>Не удалось получить публикации</AlertTitle
          ><AlertDescription
            ><Button variant="outline" @click="publications.refetch()"
              >Повторить</Button
            ></AlertDescription
          ></Alert
        >
        <Skeleton
          v-if="publications.isPending.value"
          class="h-48"
          aria-label="Загрузка списка публикаций"
        />
        <Table v-else-if="publications.data.value?.items.length">
          <TableHeader
            ><TableRow
              ><TableHead>Карточка</TableHead
              ><TableHead>SKU / внешний ID</TableHead><TableHead>Цена</TableHead
              ><TableHead>Наличие</TableHead><TableHead>Статус</TableHead
              ><TableHead>Получена</TableHead></TableRow
            ></TableHeader
          >
          <TableBody
            ><TableRow
              v-for="item in publications.data.value.items"
              :key="item.id"
            >
              <TableCell
                ><div class="flex items-center gap-3">
                  <img
                    v-if="item.thumbnail_url"
                    :src="item.thumbnail_url"
                    :alt="item.title ?? ''"
                    class="size-12 rounded-md object-contain"
                    loading="lazy"
                    referrerpolicy="no-referrer"
                  />
                  <div class="flex min-w-0 flex-col gap-1">
                    <RouterLink
                      :to="`/channels/${id}/publications/${item.id}`"
                      class="font-medium underline-offset-4 hover:underline"
                      >{{ item.title ?? "Без названия" }}</RouterLink
                    ><span
                      v-if="item.variations_count"
                      class="text-sm text-muted-foreground"
                      >Вариаций: {{ item.variations_count }}</span
                    >
                  </div>
                </div></TableCell
              >
              <TableCell
                ><div>{{ item.sku ?? "Нет SKU" }}</div>
                <div class="text-sm text-muted-foreground">
                  {{ item.external_id }}
                </div></TableCell
              >
              <TableCell>{{ priceLabel(item.price, item.currency) }}</TableCell
              ><TableCell>{{ sourceLabel(item.availability) }}</TableCell>
              <TableCell
                ><Badge variant="outline">{{
                  sourceLabel(item.source_status)
                }}</Badge></TableCell
              ><TableCell class="text-sm">{{
                dateLabel(item.observed_at)
              }}</TableCell>
            </TableRow></TableBody
          >
        </Table>
        <Empty v-else-if="!publications.isError.value"
          ><EmptyHeader
            ><EmptyTitle>{{
              active ? "Карточки загружаются" : "Публикаций пока нет"
            }}</EmptyTitle
            ><EmptyDescription>{{
              active
                ? "Список появится по мере получения страниц из источника."
                : run.data.value?.status === "succeeded"
                  ? "Источник вернул пустой список товаров."
                  : "Загрузите карточки из источника, чтобы просмотреть их поля."
            }}</EmptyDescription></EmptyHeader
          ><EmptyContent v-if="!active && supported"
            ><Button
              variant="outline"
              :disabled="pending || !channel.data.value?.is_active"
              @click="refresh"
              >Загрузить публикации</Button
            ></EmptyContent
          ></Empty
        >
      </CardContent>
      <CardFooter
        v-if="publications.data.value?.total"
        class="flex flex-wrap items-center justify-between gap-3"
      >
        <span class="text-sm text-muted-foreground"
          >{{ offset + 1 }}–{{
            Math.min(offset + 25, publications.data.value.total)
          }}
          из {{ publications.data.value.total }}</span
        >
        <div class="flex gap-2">
          <Button
            variant="outline"
            :disabled="offset === 0"
            @click="offset -= 25"
            >Назад</Button
          ><Button
            variant="outline"
            :disabled="offset + 25 >= publications.data.value.total"
            @click="offset += 25"
            >Далее</Button
          >
        </div>
      </CardFooter>
    </Card>
  </div>
</template>
