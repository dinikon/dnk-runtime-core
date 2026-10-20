<script setup lang="ts">
import { ref } from "vue";
import { Button } from "@/components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import type { PublicationIdentitySummary } from "../model/publication-identity.types";
import { identityAssessmentLabels } from "../model/publication-identity.presentation";
import { dateLabel } from "../model/channels.presentation";
defineProps<{ summary: PublicationIdentitySummary }>();
defineEmits<{ filter: [status: string] }>();
const helpOpen = ref(false);
</script>
<template>
  <Alert>
    <AlertTitle>{{ summary.label }}: проверка идентификаторов</AlertTitle>
    <AlertDescription class="flex flex-col gap-3">
      <p>
        {{ identityAssessmentLabels[summary.assessment] }} Всего:
        {{ summary.total }}.
      </p>
      <p v-if="summary.missing || summary.duplicate">
        Публикации без уникального ключа не смогут участвовать в обновлении
        через выгрузку. Связывание с каталогом и создание Draft доступны.
      </p>
      <div class="flex flex-wrap gap-2">
        <Button size="sm" variant="outline" @click="$emit('filter', 'missing')"
          >Без ключа: {{ summary.missing }}</Button
        >
        <Button
          size="sm"
          variant="outline"
          @click="$emit('filter', 'duplicate')"
          >С дублями: {{ summary.duplicate }}</Button
        >
        <Button size="sm" variant="outline" @click="$emit('filter', 'valid')"
          >Ключ указан: {{ summary.valid }}</Button
        >
        <Button size="sm" variant="ghost" @click="$emit('filter', '')"
          >Все публикации</Button
        >
        <Button size="sm" variant="ghost" @click="helpOpen = true"
          >Как исправить</Button
        >
      </div>
      <p v-if="summary.duplicateGroups" class="text-xs">
        Групп дублирующихся ключей: {{ summary.duplicateGroups }}.
      </p>
      <p v-if="summary.checkedAt" class="text-xs text-muted-foreground">
        Последняя загрузка: {{ dateLabel(summary.checkedAt) }}
      </p>
      <p
        v-if="summary.scopeLimitations.length"
        class="text-xs text-muted-foreground"
      >
        Охват источника ограничен. Проверка относится к известным платформе
        публикациям.
      </p>
    </AlertDescription>
  </Alert>
  <Dialog v-model:open="helpOpen">
    <DialogContent class="max-h-[85dvh] overflow-y-auto sm:max-w-2xl">
      <DialogHeader
        ><DialogTitle>{{ summary.helpTitle }}</DialogTitle
        ><DialogDescription
          >Ключ связывает существующую карточку площадки со строкой
          выгрузки.</DialogDescription
        ></DialogHeader
      >
      <p v-if="!summary.recoveryVerified" class="text-sm font-medium">
        Способ исправления ещё не подтверждён на тестовом товаре.
      </p>
      <ol class="list-decimal space-y-3 pl-5 text-sm">
        <li v-for="step in summary.helpSteps" :key="step">{{ step }}</li>
      </ol>
      <a
        :href="summary.helpUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="text-sm underline"
        >Документация площадки</a
      >
    </DialogContent>
  </Dialog>
</template>
