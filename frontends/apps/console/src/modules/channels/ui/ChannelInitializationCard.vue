<script setup lang="ts">
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import {
  initializationLabel,
  initializationActive,
  reasonLabel,
  dateLabel,
} from "../model/channels.presentation";
import type { Initialization } from "../model/channels.types";
defineProps<{ run: Initialization; canStart: boolean; pending: boolean }>();
defineEmits<{ start: [] }>();
</script>
<template>
  <Card aria-live="polite"
    ><CardHeader
      ><CardTitle class="flex items-center gap-2"
        ><Spinner v-if="initializationActive(run)" />{{
          initializationLabel(run)
        }}</CardTitle
      ><CardDescription
        >Первичная загрузка читает источник и сохраняет публикации в
        платформе.</CardDescription
      ></CardHeader
    ><CardContent class="flex flex-col gap-3"
      ><dl class="flex flex-wrap gap-x-10 gap-y-3">
        <div>
          <dt class="text-muted-foreground text-sm">Обработано</dt>
          <dd class="text-2xl font-semibold tabular-nums">
            {{ run.processed }}
          </dd>
        </div>
        <div>
          <dt class="text-muted-foreground text-sm">Некорректных записей</dt>
          <dd class="text-2xl font-semibold tabular-nums">{{ run.invalid }}</dd>
        </div>
        <div>
          <dt class="text-muted-foreground text-sm">Последнее обновление</dt>
          <dd class="text-sm">{{ dateLabel(run.updatedAt) }}</dd>
        </div>
      </dl>
      <p
        v-for="code in run.scopeLimitations"
        :key="code"
        class="text-muted-foreground text-sm"
      >
        {{ reasonLabel(code) }}
      </p>
      <p
        v-if="run.reasonCode && !run.scopeLimitations.includes(run.reasonCode)"
        class="text-muted-foreground text-sm"
      >
        {{ reasonLabel(run.reasonCode) }}
      </p>
      <p v-if="initializationActive(run)" class="text-muted-foreground text-sm">
        Общее количество в источнике неизвестно. Полученные публикации уже
        доступны ниже.
      </p></CardContent
    ><CardFooter v-if="!initializationActive(run)"
      ><Button
        variant="outline"
        size="sm"
        :disabled="!canStart || pending"
        @click="$emit('start')"
        >{{
          pending
            ? "Отправляем…"
            : run.readComplete
              ? "Обновить публикации"
              : "Продолжить загрузку"
        }}</Button
      ></CardFooter
    ></Card
  >
</template>
