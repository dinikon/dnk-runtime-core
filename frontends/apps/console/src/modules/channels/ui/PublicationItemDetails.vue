<script setup lang="ts">
import { Image } from "@lucide/vue";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { PublicationItem } from "../model/publication.types";
withDefaults(
  defineProps<{
    item: PublicationItem;
    primary?: boolean;
    highlighted?: boolean;
    compact?: boolean;
  }>(),
  { primary: false, highlighted: false, compact: false },
);
function externalUrl(value: string | null | undefined): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) &&
      !url.username &&
      !url.password
      ? url.href
      : undefined;
  } catch {
    return undefined;
  }
}
</script>
<template>
  <Card
    :class="{ 'ring-2 ring-ring': highlighted, 'gap-3 py-3': compact }"
    :aria-current="highlighted ? 'true' : undefined"
    data-slot="publication-item-details"
  >
    <CardHeader :class="{ 'px-3': compact }">
      <CardTitle class="min-w-0 break-words">{{
        item.title ?? "Перевод не получен"
      }}</CardTitle>
      <div v-if="primary || highlighted" class="flex flex-wrap gap-2">
        <Badge v-if="primary" variant="secondary">Основная позиция</Badge>
        <Badge v-if="highlighted" variant="outline">Позиция из ссылки</Badge>
      </div>
    </CardHeader>
    <CardContent
      class="flex min-w-0 flex-col gap-4"
      :class="{ 'gap-2 px-3': compact }"
    >
      <p
        v-if="item.staleConfiguration"
        role="status"
        class="text-sm text-muted-foreground"
      >
        Снимок получен с предыдущими настройками канала. Ожидается повторная
        синхронизация.
      </p>
      <div
        class="grid min-w-0"
        :class="
          compact
            ? 'grid-cols-[48px_minmax(0,1fr)] gap-3'
            : 'gap-6 sm:grid-cols-[minmax(0,200px)_1fr]'
        "
      >
        <Avatar
          class="rounded-md"
          :class="compact ? 'size-12' : 'size-40 sm:size-48'"
        >
          <AvatarImage
            v-if="externalUrl(item.mainImageUrl)"
            :key="item.mainImageUrl ?? undefined"
            :src="externalUrl(item.mainImageUrl) ?? ''"
            :alt="item.title ?? ''"
            class="object-contain"
          />
          <AvatarFallback class="rounded-md"
            ><Image aria-hidden="true"
          /></AvatarFallback>
        </Avatar>
        <dl
          class="grid min-w-0 text-sm"
          :class="
            compact
              ? 'grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 lg:grid-cols-[auto_minmax(0,1fr)_auto_minmax(0,1fr)_auto_minmax(0,1fr)]'
              : 'grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-[auto_minmax(0,1fr)] sm:gap-y-3'
          "
        >
          <dt class="text-muted-foreground">ID площадки</dt>
          <dd class="break-all">{{ item.externalId }}</dd>
          <dt class="text-muted-foreground">Артикул</dt>
          <dd class="min-w-0 break-words">
            {{ item.sku ?? "Не получен" }}
          </dd>
          <dt class="text-muted-foreground">Цена</dt>
          <dd class="min-w-0 break-words">
            {{
              item.price === null
                ? "Не получена"
                : item.price + " " + item.currency
            }}
          </dd>
          <dt class="text-muted-foreground">Остаток</dt>
          <dd class="min-w-0 break-words">
            {{ item.quantity ?? "Не получен"
            }}<span
              v-if="item.stockMode === 'parent'"
              class="ml-2 text-muted-foreground"
              >Общий остаток карточки</span
            >
          </dd>
          <dt class="text-muted-foreground">Наличие</dt>
          <dd>
            {{
              item.availability === "in_stock"
                ? "В наличии"
                : item.availability === "out_of_stock"
                  ? "Нет в наличии"
                  : item.availability === "on_order"
                    ? "Под заказ"
                    : item.availability === "removed"
                      ? "Удалён из прайса"
                      : "Не получено"
            }}
          </dd>
          <dt class="text-muted-foreground">Статус площадки</dt>
          <dd class="min-w-0 break-words">
            {{ item.status ?? "Не получен" }}
          </dd>
          <dt class="text-muted-foreground">Получено</dt>
          <dd class="min-w-0 break-words">
            {{ new Date(item.lastSeenAt).toLocaleString() }}
          </dd>
        </dl>
      </div>
      <a
        v-if="externalUrl(item.url)"
        :href="externalUrl(item.url)"
        target="_blank"
        rel="noopener noreferrer"
        class="inline-block text-sm underline"
        >Открыть на площадке</a
      >
    </CardContent>
  </Card>
</template>
