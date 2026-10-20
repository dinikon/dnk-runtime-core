<script setup lang="ts">
import { computed } from "vue";
import DOMPurify from "dompurify";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type {
  ContentUpdateItem,
  ContentText,
} from "../model/content-update.types";
import { contentUpdateLabels } from "../model/content-update.presentation";
import { reasonLabel } from "../model/channels.presentation";
const props = defineProps<{
  item: ContentUpdateItem;
  locale: string;
  confirmed?: boolean;
}>();
defineEmits<{ openCatalog: [id: string, locale: string] }>();
const desired = computed(() =>
  props.item.desired.find((text) => text.locale === props.locale),
);
const observed = computed(() =>
  props.item.observed.find((text) => text.locale === props.locale),
);
function safeBody(text: ContentText | undefined): string {
  return DOMPurify.sanitize(text?.body ?? "", {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["img", "video", "audio", "iframe", "form", "style"],
  });
}
</script>
<template>
  <Card class="min-w-0">
    <CardHeader>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="min-w-0">
          <CardTitle class="break-words">{{
            desired?.title ?? "Товар каталога"
          }}</CardTitle>
          <CardDescription
            >Публикация {{ item.externalId }} · {{ locale }}</CardDescription
          >
        </div>
        <Badge variant="outline">{{
          contentUpdateLabels[item.status] ?? item.status
        }}</Badge>
      </div>
      <Button
        variant="link"
        size="sm"
        class="w-fit px-0"
        @click="$emit('openCatalog', item.catalogItemId, locale)"
        >Открыть товар в каталоге</Button
      >
    </CardHeader>
    <CardContent class="flex flex-col gap-4">
      <Alert v-for="issue in item.issues" :key="issue"
        ><AlertDescription>{{ reasonLabel(issue) }}</AlertDescription></Alert
      >
      <div class="grid min-w-0 gap-4 lg:grid-cols-2">
        <section
          class="min-w-0 rounded-lg border p-4"
          :aria-label="confirmed ? 'Перед обновлением' : 'Сейчас на площадке'"
        >
          <h3 class="text-muted-foreground mb-4 text-sm font-medium">
            {{ confirmed ? "Перед обновлением" : "Сейчас на площадке" }}
          </h3>
          <p class="mb-3 font-medium break-words">
            {{ observed?.title ?? "Название не получено" }}
          </p>
          <!-- The source is sanitized at the API boundary and again before rendering. -->
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div
            v-if="observed?.body"
            class="content-preview text-sm break-words"
            v-html="safeBody(observed)"
          />
          <p v-else class="text-muted-foreground text-sm">
            Описание не получено
          </p>
        </section>
        <section
          class="min-w-0 rounded-lg border p-4"
          aria-label="Будет из каталога"
        >
          <h3 class="text-muted-foreground mb-4 text-sm font-medium">
            Будет из каталога
          </h3>
          <p class="mb-3 font-medium break-words">
            {{ desired?.title ?? "Заполните название в каталоге" }}
          </p>
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div
            v-if="desired?.body"
            class="content-preview text-sm break-words"
            v-html="safeBody(desired)"
          />
          <p v-else class="text-muted-foreground text-sm">
            Заполните описание в каталоге
          </p>
        </section>
      </div>
    </CardContent>
  </Card>
</template>
<style scoped>
.content-preview {
  overflow-wrap: anywhere;
}
.content-preview :deep(p + p) {
  margin-top: 0.75rem;
}
.content-preview :deep(ul) {
  list-style: disc;
  padding-left: 1.25rem;
}
.content-preview :deep(ol) {
  list-style: decimal;
  padding-left: 1.25rem;
}
.content-preview :deep(pre) {
  white-space: pre-wrap;
}
.content-preview :deep(table) {
  display: block;
  max-width: 100%;
  overflow-x: auto;
}
</style>
