<script setup lang="ts">
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import type { Publication } from "../model/channels.types";
import {
  decimalLabel,
  dateLabel,
  stockLabels,
  reasonLabel,
} from "../model/channels.presentation";
defineProps<{ items: Publication[] }>();
function safeImage(value: string | null): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.href : undefined;
  } catch {
    return undefined;
  }
}
</script>
<template>
  <Table
    ><TableHeader
      ><TableRow
        ><TableHead class="min-w-64">Публикация</TableHead
        ><TableHead>ID / SKU</TableHead><TableHead>Цена</TableHead
        ><TableHead>Акционная цена</TableHead><TableHead>Количество</TableHead
        ><TableHead>Наличие</TableHead><TableHead>Получено</TableHead></TableRow
      ></TableHeader
    ><TableBody
      ><TableRow v-for="item in items" :key="item.id"
        ><TableCell
          ><div class="flex items-start gap-3">
            <Avatar class="size-12 shrink-0 rounded-md"
              ><AvatarImage
                v-if="safeImage(item.mainImageUrl)"
                :src="safeImage(item.mainImageUrl) ?? ''"
                alt=""
                loading="lazy"
                referrerpolicy="no-referrer"
              /><AvatarFallback class="rounded-md">—</AvatarFallback></Avatar
            >
            <div class="flex max-w-80 min-w-0 flex-col gap-1">
              <span class="font-medium whitespace-normal">{{
                item.title ?? "Без названия"
              }}</span
              ><span
                v-if="item.titleLocale"
                class="text-muted-foreground text-xs"
                >{{ item.titleLocale }}</span
              >
              <details
                v-if="item.warnings.length"
                class="text-muted-foreground text-xs"
              >
                <summary class="cursor-pointer">
                  Предупреждения: {{ item.warnings.length }}
                </summary>
                <ul class="mt-2 flex list-disc flex-col gap-1 pl-4">
                  <li
                    v-for="warning in item.warnings"
                    :key="warning"
                    class="whitespace-normal"
                  >
                    {{ reasonLabel(warning) }}
                  </li>
                </ul>
              </details>
            </div>
          </div></TableCell
        ><TableCell
          ><div>{{ item.externalId }}</div>
          <div class="text-muted-foreground">
            {{ item.externalSku ?? "SKU не указан" }}
          </div></TableCell
        ><TableCell class="tabular-nums">{{
          decimalLabel(item.price, item.currency)
        }}</TableCell
        ><TableCell class="tabular-nums">{{
          decimalLabel(item.salePrice, item.currency)
        }}</TableCell
        ><TableCell class="tabular-nums">{{
          decimalLabel(item.quantity)
        }}</TableCell
        ><TableCell
          ><Badge variant="outline">{{
            stockLabels[item.stockStatus] ?? "Неизвестно"
          }}</Badge></TableCell
        ><TableCell class="text-muted-foreground text-xs">{{
          dateLabel(item.lastSeenAt)
        }}</TableCell></TableRow
      ></TableBody
    ></Table
  >
</template>
