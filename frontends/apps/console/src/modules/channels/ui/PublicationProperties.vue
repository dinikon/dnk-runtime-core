<script setup lang="ts">
import { computed } from "vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";
import { Image, ExternalLink } from "@lucide/vue";
import type { PublicationCard } from "../model/publication.types";
import type { Channel } from "../model/channel.types";
import {
  publicationPrice,
  publicationStock,
} from "../model/publication-summary";
import {
  publicationThumbnail,
  publicationExternalUrl,
} from "../model/publication.thumbnail";
import ChannelSettingsSection from "./ChannelSettingsSection.vue";

const props = defineProps<{
  card: PublicationCard;
  channel?: Channel;
  locale: string;
  locales: string[];
  busy: boolean;
}>();
defineEmits<{ locale: [value: string]; channel: [] }>();
const kindLabels: Record<string, string> = {
  simple: "Самостоятельная",
  variable: "С вариантами",
  variant: "Вариант",
};
const platformLabels: Record<string, string> = {
  woocommerce: "WooCommerce",
  prom: "Prom",
  rozetka: "Rozetka",
};
const languageLabels: Record<string, string> = {
  ru: "Русский",
  uk: "Українська",
  en: "English",
};
const external = computed(() =>
  publicationExternalUrl(
    props.card.rootKind === "simple"
      ? props.card.items.find((item) => item.id === props.card.id)?.url
      : null,
  ),
);
const identity = computed(() => [
  { label: "ID площадки", value: props.card.rootExternalId },
  {
    label: "Артикул",
    value:
      props.card.rootSku ??
      (props.card.rootKind === "simple"
        ? props.card.items.find((item) => item.id === props.card.id)?.sku
        : null) ??
      "Не получен",
  },
  {
    label: "Тип",
    value: kindLabels[props.card.rootKind] ?? props.card.rootKind,
  },
  { label: "Позиции", value: String(props.card.items.length) },
]);
</script>
<template>
  <div class="channel-settings-sections">
    <div class="border-b py-4">
      <h1 class="break-words text-lg font-semibold">
        {{ card.title ?? "Перевод не получен" }}
      </h1>
    </div>
    <ChannelSettingsSection title="Основные сведения">
      <dl class="grid grid-cols-[112px_minmax(0,1fr)] gap-x-3 gap-y-3 text-sm">
        <template v-for="field in identity" :key="field.label"
          ><dt class="text-muted-foreground">{{ field.label }}</dt>
          <dd class="min-w-0 break-words">{{ field.value }}</dd></template
        >
      </dl>
      <Button
        v-if="external"
        as-child
        variant="link"
        size="sm"
        class="mt-2 h-auto max-w-full px-0"
        ><a :href="external" target="_blank" rel="noopener noreferrer"
          ><ExternalLink data-icon="inline-start" />Открыть на площадке</a
        ></Button
      >
    </ChannelSettingsSection>
    <ChannelSettingsSection title="Цена и остаток">
      <dl class="grid grid-cols-[112px_minmax(0,1fr)] gap-x-3 gap-y-3 text-sm">
        <dt class="text-muted-foreground">Стоимость</dt>
        <dd class="min-w-0 break-all tabular-nums">
          {{ publicationPrice(card) }}
        </dd>
        <dt class="text-muted-foreground">Остаток</dt>
        <dd class="min-w-0 break-words tabular-nums">
          {{ publicationStock(card) }}
        </dd>
      </dl>
      <p class="mt-3 text-xs text-muted-foreground">
        Данные обновляются при синхронизации подключения.
      </p>
    </ChannelSettingsSection>
    <ChannelSettingsSection title="Связь с каталогом"
      ><slot name="catalog"
    /></ChannelSettingsSection>
    <ChannelSettingsSection title="Подключение">
      <dl class="grid grid-cols-[112px_minmax(0,1fr)] gap-x-3 gap-y-3 text-sm">
        <dt class="text-muted-foreground">Магазин</dt>
        <dd>
          <Button
            type="button"
            variant="link"
            size="sm"
            class="h-auto max-w-full p-0 text-left"
            :disabled="busy"
            @click="$emit('channel')"
            ><span class="truncate">{{
              channel?.name ?? "Подключение"
            }}</span></Button
          >
        </dd>
        <dt class="text-muted-foreground">Площадка</dt>
        <dd>
          {{
            platformLabels[channel?.platformKind ?? ""] ??
            channel?.platformKind ??
            "Не получена"
          }}
        </dd>
        <dt class="text-muted-foreground">Получено</dt>
        <dd>{{ new Date(card.lastSeenAt).toLocaleString("ru-RU") }}</dd>
      </dl>
      <div class="mt-3 flex flex-col gap-2">
        <Label :for="locales.length > 1 ? 'publication-locale' : undefined"
          >Язык публикации</Label
        ><Select
          v-if="locales.length > 1"
          :model-value="locale"
          :disabled="busy"
          @update:model-value="$event && $emit('locale', String($event))"
          ><SelectTrigger id="publication-locale" class="w-full"
            ><SelectValue /></SelectTrigger
          ><SelectContent
            ><SelectGroup
              ><SelectItem
                v-for="language in locales"
                :key="language"
                :value="language"
                >{{ languageLabels[language] ?? language }}</SelectItem
              ></SelectGroup
            ></SelectContent
          ></Select
        >
        <p v-else class="text-sm">{{ languageLabels[locale] ?? locale }}</p>
      </div>
      <Badge
        v-if="card.items.some((item) => item.staleConfiguration)"
        variant="outline"
        class="mt-3 whitespace-normal"
        >Получено с предыдущими настройками</Badge
      >
    </ChannelSettingsSection>
    <ChannelSettingsSection title="Изображение">
      <Avatar class="aspect-square size-auto w-full rounded-lg bg-muted"
        ><AvatarImage
          v-if="publicationThumbnail(card)"
          :src="publicationThumbnail(card) ?? ''"
          :alt="card.title ?? 'Изображение публикации'"
          class="object-contain" /><AvatarFallback class="rounded-lg"
          ><Image class="size-10 text-muted-foreground" /></AvatarFallback
      ></Avatar>
    </ChannelSettingsSection>
  </div>
</template>
