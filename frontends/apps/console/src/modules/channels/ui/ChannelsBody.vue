<script setup lang="ts">
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
  EmptyContent,
} from "@/components/ui/empty";
import ChannelsTable from "./ChannelsTable.vue";
import type { Channel, Platform } from "../model/channel.types";
defineProps<{
  loading: boolean;
  error: string;
  items: Channel[];
  platforms: Platform[];
  filtered: boolean;
  outOfRange: boolean;
}>();
const emit = defineEmits<{
  retry: [];
  open: [id: string];
  create: [];
  reset: [];
  firstPage: [];
}>();
</script>
<template>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col gap-3" :aria-busy="loading">
    <Alert v-if="error" variant="destructive" class="shrink-0"
      ><AlertDescription
        class="flex flex-wrap items-center justify-between gap-3"
        >{{ error
        }}<Button variant="outline" @click="emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <ChannelsTable
      v-if="items.length"
      :items="items"
      :platforms="platforms"
      @open="emit('open', $event)"
    />
    <div
      v-else-if="loading && !error"
      role="status"
      aria-label="Загрузка подключений"
      class="flex flex-col gap-2"
    >
      <Skeleton class="h-10 w-full" /><Skeleton
        v-for="row in 5"
        :key="row"
        class="h-10 w-full"
      />
    </div>
    <Empty v-else-if="!error" class="min-h-60"
      ><EmptyHeader
        ><EmptyTitle>{{
          outOfRange
            ? "На этой странице нет подключений"
            : filtered
              ? "Подключения не найдены"
              : "Подключений пока нет"
        }}</EmptyTitle
        ><EmptyDescription>{{
          outOfRange
            ? "Вернитесь на первую страницу списка."
            : filtered
              ? "Измените поиск или сбросьте фильтры."
              : "Подключите магазин и проверьте доступ к площадке."
        }}</EmptyDescription></EmptyHeader
      ><EmptyContent
        ><Button v-if="outOfRange" variant="outline" @click="emit('firstPage')"
          >На первую страницу</Button
        ><Button v-else-if="filtered" variant="outline" @click="emit('reset')"
          >Сбросить фильтры</Button
        ><Button v-else @click="emit('create')"
          >Подключить магазин</Button
        ></EmptyContent
      ></Empty
    >
  </div>
</template>
