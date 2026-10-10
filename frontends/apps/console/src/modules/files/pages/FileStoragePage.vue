<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { useFileStorage } from "../model/queries";
import { bucketStatusLabels, formatStorageBytes } from "../model/types";
const { providers, buckets } = useFileStorage();
const loading = computed(
  () => providers.isPending.value || buckets.isPending.value,
);
const failed = computed(() => providers.isError.value || buckets.isError.value);
const refreshing = computed(
  () => providers.isFetching.value || buckets.isFetching.value,
);
const connections = computed(() =>
  (providers.data.value ?? []).map((provider) => ({
    ...provider,
    buckets: (buckets.data.value ?? []).filter(
      (bucket) => bucket.provider_id === provider.id,
    ),
  })),
);
async function refresh() {
  await Promise.all([providers.refetch(), buckets.refetch()]);
}
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Файловые хранилища</h1>
        <p class="text-sm text-muted-foreground">
          Подключения и приватные бакеты вашего рабочего пространства
        </p>
      </div>
      <Button variant="outline" :disabled="refreshing" @click="refresh"
        >Обновить</Button
      >
    </header>
    <Skeleton v-if="loading" class="h-48" aria-label="Загрузка хранилищ" />
    <Alert v-else-if="failed" variant="destructive">
      <AlertTitle>Не удалось загрузить хранилища</AlertTitle>
      <AlertDescription
        >Повторите попытку с помощью кнопки «Обновить».</AlertDescription
      >
    </Alert>
    <Card v-else-if="!connections.length">
      <CardHeader
        ><CardTitle>Подключения</CardTitle
        ><CardDescription
          >Доступные файловые хранилища</CardDescription
        ></CardHeader
      >
      <CardContent
        ><Empty
          ><EmptyHeader
            ><EmptyTitle>Хранилище ещё не подготовлено</EmptyTitle
            ><EmptyDescription
              >Системное подключение появится после подготовки рабочего
              пространства.</EmptyDescription
            ></EmptyHeader
          ></Empty
        ></CardContent
      >
    </Card>
    <template v-else>
      <Card v-for="connection in connections" :key="connection.id">
        <CardHeader>
          <div class="flex flex-wrap items-center gap-2">
            <CardTitle>{{ connection.name }}</CardTitle>
            <Badge v-if="connection.is_system" variant="secondary"
              >Default / System</Badge
            >
          </div>
          <CardDescription
            >{{ connection.kind === "minio" ? "MinIO" : connection.kind }} ·
            Только просмотр</CardDescription
          >
        </CardHeader>
        <CardContent>
          <Empty v-if="!connection.buckets.length"
            ><EmptyHeader
              ><EmptyTitle>Бакетов пока нет</EmptyTitle
              ><EmptyDescription
                >Бакеты появятся после подготовки хранилища.</EmptyDescription
              ></EmptyHeader
            ></Empty
          >
          <template v-else>
            <div class="space-y-3 sm:hidden">
              <div
                v-for="bucket in connection.buckets"
                :key="bucket.id"
                class="space-y-3 rounded-md border p-3"
              >
                <p class="break-all text-sm font-medium">{{ bucket.name }}</p>
                <Badge variant="outline">{{
                  bucketStatusLabels[bucket.status]
                }}</Badge>
                <dl class="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt class="text-muted-foreground">Файлы</dt>
                    <dd class="tabular-nums">
                      {{ bucket.files_count.toLocaleString("ru") }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-muted-foreground">Используется</dt>
                    <dd class="tabular-nums">
                      {{ formatStorageBytes(bucket.size_bytes) }}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
            <Table class="hidden sm:table">
              <TableHeader
                ><TableRow
                  ><TableHead>Бакет</TableHead><TableHead>Состояние</TableHead
                  ><TableHead class="text-right">Файлы</TableHead
                  ><TableHead class="text-right"
                    >Используется</TableHead
                  ></TableRow
                ></TableHeader
              >
              <TableBody
                ><TableRow
                  v-for="bucket in connection.buckets"
                  :key="bucket.id"
                >
                  <TableCell
                    class="max-w-64 break-all whitespace-normal font-medium"
                    >{{ bucket.name }}</TableCell
                  >
                  <TableCell
                    ><Badge variant="outline">{{
                      bucketStatusLabels[bucket.status]
                    }}</Badge></TableCell
                  >
                  <TableCell class="text-right tabular-nums">{{
                    bucket.files_count.toLocaleString("ru")
                  }}</TableCell>
                  <TableCell
                    class="text-right whitespace-nowrap tabular-nums"
                    >{{ formatStorageBytes(bucket.size_bytes) }}</TableCell
                  >
                </TableRow></TableBody
              >
            </Table>
          </template>
          <p
            v-if="connection.buckets.length"
            class="mt-3 text-sm text-muted-foreground"
          >
            Объём зарегистрированных файлов без служебных расходов хранилища.
          </p>
        </CardContent>
      </Card>
    </template>
  </div>
</template>
