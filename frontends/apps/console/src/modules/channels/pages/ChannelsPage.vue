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
  EmptyContent,
} from "@/components/ui/empty";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { useChannels, useKinds } from "../model/queries";
import { statusLabels, typeLabels } from "../model/types";
const channels = useChannels();
const kinds = useKinds();
const labels = computed(() =>
  Object.fromEntries((kinds.data.value ?? []).map((k) => [k.kind, k.label])),
);
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Каналы</h1>
        <p class="text-sm text-muted-foreground">
          Магазины и площадки, с которыми вы работаете
        </p>
      </div>
      <Button as-child
        ><RouterLink to="/channels/new">Добавить канал</RouterLink></Button
      >
    </header>
    <Card>
      <CardHeader
        ><CardTitle>Ваши подключения</CardTitle
        ><CardDescription
          >Активность канала и состояние подключения отображаются
          отдельно.</CardDescription
        ></CardHeader
      >
      <CardContent>
        <Skeleton
          v-if="channels.isPending.value || kinds.isPending.value"
          class="h-48"
          aria-label="Загрузка каналов"
        />
        <Alert
          v-else-if="channels.isError.value || kinds.isError.value"
          variant="destructive"
        >
          <AlertTitle>Не удалось загрузить каналы</AlertTitle
          ><AlertDescription
            ><Button
              variant="outline"
              :disabled="channels.isFetching.value || kinds.isFetching.value"
              @click="
                channels.refetch();
                kinds.refetch();
              "
              >Повторить</Button
            ></AlertDescription
          >
        </Alert>
        <Empty v-else-if="!channels.data.value?.length"
          ><EmptyHeader
            ><EmptyTitle>Каналов пока нет</EmptyTitle
            ><EmptyDescription
              >Добавьте магазин или маркетплейс и сохраните его настройки
              подключения.</EmptyDescription
            ></EmptyHeader
          ><EmptyContent
            ><Button as-child
              ><RouterLink to="/channels/new"
                >Добавить первый канал</RouterLink
              ></Button
            ></EmptyContent
          ></Empty
        >
        <Table v-else>
          <TableHeader
            ><TableRow
              ><TableHead>Название</TableHead><TableHead>Платформа</TableHead
              ><TableHead>Категория</TableHead><TableHead>Активность</TableHead
              ><TableHead>Подключение</TableHead></TableRow
            ></TableHeader
          >
          <TableBody
            ><TableRow v-for="item in channels.data.value" :key="item.id">
              <TableCell
                ><RouterLink
                  :to="`/channels/${item.id}`"
                  class="font-medium underline-offset-4 hover:underline"
                  >{{ item.name }}</RouterLink
                ></TableCell
              >
              <TableCell>{{ labels[item.kind] ?? item.kind }}</TableCell
              ><TableCell>{{ typeLabels[item.type] }}</TableCell>
              <TableCell>{{
                item.is_active ? "Включён" : "Выключен"
              }}</TableCell
              ><TableCell
                ><Badge
                  :variant="
                    item.status === 'error' ? 'destructive' : 'secondary'
                  "
                  >{{ statusLabels[item.status] }}</Badge
                ></TableCell
              >
            </TableRow></TableBody
          >
        </Table>
      </CardContent>
    </Card>
  </div>
</template>
