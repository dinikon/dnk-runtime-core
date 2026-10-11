<script setup lang="ts">
import { FileText, Image, Video, Files, ArrowRight } from "@lucide/vue";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  categoryLabels,
  formatStorageBytes,
  type FileCategory,
  type FilesOverviewResult,
} from "../model/types";
defineProps<{ data: FilesOverviewResult; selected?: FileCategory }>();
defineEmits<{ select: [category: FileCategory] }>();
const icons = {
  documents: FileText,
  images: Image,
  videos: Video,
  other: Files,
};
</script>
<template>
  <div class="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
    <Card
      v-for="item in data.categories"
      :key="item.category"
      :class="selected === item.category ? 'border-primary' : ''"
    >
      <CardHeader
        ><div class="flex items-center justify-between gap-2">
          <CardTitle class="text-sm">{{
            categoryLabels[item.category]
          }}</CardTitle
          ><component
            :is="icons[item.category]"
            class="size-5 text-muted-foreground"
          />
        </div>
        <CardDescription>Активные файлы</CardDescription></CardHeader
      >
      <CardContent class="flex flex-col gap-2"
        ><p class="text-3xl font-semibold tabular-nums">
          {{ item.files_count.toLocaleString("ru") }}
        </p>
        <p class="text-sm text-muted-foreground">
          {{ formatStorageBytes(item.size_bytes) }}
        </p></CardContent
      >
      <CardFooter class="border-t"
        ><Button
          variant="ghost"
          class="ml-auto"
          :aria-pressed="selected === item.category"
          @click="$emit('select', item.category)"
          >Показать<ArrowRight data-icon="inline-end" /><span class="sr-only">{{
            categoryLabels[item.category]
          }}</span></Button
        ></CardFooter
      >
    </Card>
  </div>
  <Card
    ><CardHeader
      ><CardTitle class="text-base">Объём зарегистрированных файлов</CardTitle
      ><CardDescription
        >Сводка по выбранным дискам. Объём корзины включает файлы, ожидающие
        окончательного удаления.</CardDescription
      ></CardHeader
    >
    <CardContent
      ><dl class="grid grid-cols-3 gap-3 sm:gap-4">
        <div>
          <dt class="text-sm text-muted-foreground">
            Активные · {{ data.active_count }}
          </dt>
          <dd class="text-xl font-semibold tabular-nums">
            {{ formatStorageBytes(data.active_size_bytes) }}
          </dd>
        </div>
        <div>
          <dt class="text-sm text-muted-foreground">
            В корзине · {{ data.trashed_count }}
          </dt>
          <dd class="text-xl font-semibold tabular-nums">
            {{ formatStorageBytes(data.trashed_size_bytes) }}
          </dd>
        </div>
        <div>
          <dt class="text-sm text-muted-foreground">
            Удаляются · {{ data.pending_purge_count }}
          </dt>
          <dd class="text-xl font-semibold tabular-nums">
            {{ formatStorageBytes(data.pending_purge_size_bytes) }}
          </dd>
        </div>
      </dl></CardContent
    ></Card
  >
</template>
