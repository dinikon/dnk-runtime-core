<script setup lang="ts">
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { StockLocation } from "../../model/stock-location.types";
defineProps<{
  locationId: string | null;
  location?: StockLocation;
  loading: boolean;
  error: string;
  disabled: boolean;
  saved: boolean;
}>();
const emit = defineEmits<{ change: []; retry: [] }>();
</script>

<template>
  <Card
    class="w-full max-w-4xl shrink-0"
    aria-label="Основная локация хранения"
  >
    <CardHeader>
      <CardTitle>Основная локация хранения</CardTitle>
      <CardDescription
        >Используется как основная STORAGE-локация склада.</CardDescription
      >
    </CardHeader>
    <CardContent class="flex flex-col gap-3" :aria-busy="loading">
      <p v-if="!locationId" class="text-sm text-muted-foreground">
        Не назначена
      </p>
      <p v-else-if="location" class="break-words text-sm">
        <span class="font-mono break-all">{{ location.code }}</span> —
        {{ location.name }}
      </p>
      <div
        v-else-if="loading"
        role="status"
        aria-label="Загрузка основной локации"
      >
        <Skeleton class="h-6 w-full max-w-md" />
      </div>
      <Alert v-if="error" variant="destructive">
        <AlertDescription class="flex flex-wrap items-center gap-2">
          <span>{{ error }}</span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="disabled || loading"
            @click="emit('retry')"
            >Повторить загрузку основной локации</Button
          >
        </AlertDescription>
      </Alert>
      <p v-if="saved" role="status" class="text-sm text-muted-foreground">
        Основная локация назначена.
      </p>
    </CardContent>
    <CardFooter
      ><Button
        type="button"
        variant="outline"
        :disabled="disabled"
        @click="emit('change')"
        >{{
          locationId
            ? "Изменить основную локацию"
            : "Назначить основную локацию"
        }}</Button
      ></CardFooter
    >
  </Card>
</template>
