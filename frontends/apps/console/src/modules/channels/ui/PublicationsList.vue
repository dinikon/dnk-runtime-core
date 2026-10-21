<script setup lang="ts">
import PublicationIdentityBadge from "./PublicationIdentityBadge.vue";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import type { Publication } from "../model/channels.types";
import {
  decimalLabel,
  dateLabel,
  stockLabels,
  reasonLabel,
} from "../model/channels.presentation";
defineProps<{
  items: Publication[];
  identityLabel?: string;
  archived?: boolean;
  busy?: boolean;
  canImport?: boolean;
  canUpdate?: boolean;
  canExport?: boolean;
  selectedIds?: string[];
}>();
defineEmits<{
  duplicates: [key: string];
  bind: [publication: Publication];
  draft: [publication: Publication];
  unbind: [publication: Publication];
  openCatalog: [publication: Publication];
  updateTexts: [publication: Publication];
  select: [id: string, selected: boolean];
  export: [publication: Publication, enabled: boolean];
}>();
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
        ><TableHead v-if="canUpdate || canExport" class="w-12">Выбор</TableHead
        ><TableHead class="min-w-64">Публикация</TableHead
        ><TableHead>ID / SKU</TableHead
        ><TableHead v-if="identityLabel">{{ identityLabel }}</TableHead
        ><TableHead>Цена</TableHead><TableHead>Акционная цена</TableHead
        ><TableHead>Количество</TableHead><TableHead>Наличие</TableHead
        ><TableHead>Получено</TableHead
        ><TableHead class="min-w-48">Товар каталога</TableHead></TableRow
      ></TableHeader
    ><TableBody
      ><TableRow v-for="item in items" :key="item.id"
        ><TableCell v-if="canUpdate || canExport"
          ><Checkbox
            :aria-label="`Выбрать публикацию ${item.externalId}`"
            :model-value="selectedIds?.includes(item.id) ?? false"
            :disabled="busy || archived || !item.catalogItemId"
            @update:model-value="
              (value) => $emit('select', item.id, value === true)
            " /></TableCell
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
        ><TableCell v-if="identityLabel"
          ><PublicationIdentityBadge
            v-if="item.identity"
            :identity="item.identity"
            :label="identityLabel"
            @duplicates="(key) => $emit('duplicates', key)" /></TableCell
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
        }}</TableCell
        ><TableCell
          ><div class="flex flex-col items-start gap-2">
            <template v-if="item.catalogItemId"
              ><Button
                variant="link"
                size="sm"
                class="h-auto p-0"
                @click="$emit('openCatalog', item)"
                >Открыть товар</Button
              ><span class="text-muted-foreground text-xs">{{
                item.catalogItemId.slice(0, 8)
              }}</span
              ><Button
                v-if="canUpdate"
                variant="outline"
                size="sm"
                :disabled="busy || archived"
                @click="$emit('updateTexts', item)"
                >Обновить тексты</Button
              ><Badge v-if="canExport" variant="outline">{{
                item.exportEnabled ? "Экспорт разрешён" : "Экспорт выключен"
              }}</Badge
              ><Button
                v-if="canExport"
                variant="outline"
                size="sm"
                :disabled="busy || archived"
                @click="$emit('export', item, !item.exportEnabled)"
                >{{
                  item.exportEnabled ? "Выключить экспорт" : "Разрешить экспорт"
                }}</Button
              ><Button
                variant="outline"
                size="sm"
                :disabled="busy"
                @click="$emit('unbind', item)"
                >Снять связь</Button
              ></template
            >
            <template v-else
              ><span class="text-muted-foreground text-xs">Не связано</span
              ><Button
                variant="outline"
                size="sm"
                :disabled="busy || archived"
                @click="$emit('bind', item)"
                >Связать с товаром</Button
              ><Button
                variant="outline"
                size="sm"
                :disabled="busy || archived || !canImport"
                @click="$emit('draft', item)"
                >Создать Draft</Button
              ></template
            >
          </div></TableCell
        ></TableRow
      ></TableBody
    ></Table
  >
</template>
