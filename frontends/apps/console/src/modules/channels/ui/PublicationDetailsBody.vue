<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { PublicationCard } from "../model/publication.types";
import PublicationItemDetails from "./PublicationItemDetails.vue";
const props = defineProps<{
  card: PublicationCard | undefined;
  pending: boolean;
  error: string;
  requestedPublicationId: string;
}>();
const emit = defineEmits<{ retry: [] }>();
const hasVariants = computed(
  () =>
    !!props.card &&
    (props.card.rootKind === "variable" ||
      props.card.items.length > 1 ||
      props.card.items.some((item) => item.kind === "variant")),
);
</script>
<template>
  <Alert v-if="error" variant="destructive">
    <AlertDescription class="flex flex-wrap items-center gap-3">
      {{ error }}
      <Button variant="outline" @click="emit('retry')">Повторить</Button>
    </AlertDescription>
  </Alert>
  <Skeleton v-if="pending" class="h-80 w-full shrink-0" />
  <div v-else-if="card" class="flex min-w-0 flex-col gap-6">
    <template v-if="hasVariants || !card.items.length">
      <Card>
        <CardHeader
          ><CardTitle class="break-words">{{
            card.title ?? "Перевод не получен"
          }}</CardTitle></CardHeader
        >
        <CardContent>
          <p class="text-sm">
            <span class="text-muted-foreground">Цена: </span
            >{{
              card.minPrice === null
                ? "Не получена"
                : card.minPrice +
                  (card.maxPrice !== null && card.maxPrice !== card.minPrice
                    ? "–" + card.maxPrice
                    : "") +
                  " " +
                  (card.currency ?? "")
            }}
          </p>
        </CardContent>
      </Card>
      <section aria-label="Варианты" class="flex min-w-0 flex-col gap-3">
        <h2 class="text-lg font-semibold">Варианты</h2>
        <p v-if="!card.items.length" class="text-sm text-muted-foreground">
          Разновидности этой карточки ещё не получены.
        </p>
        <ul v-else class="flex min-w-0 flex-col gap-3">
          <li v-for="item in card.items" :key="item.id" class="min-w-0">
            <PublicationItemDetails
              compact
              :item="item"
              :primary="card.rootKind === 'simple' && item.id === card.id"
              :highlighted="
                requestedPublicationId !== card.id &&
                item.id === requestedPublicationId
              "
            />
          </li>
        </ul>
      </section>
    </template>
    <PublicationItemDetails
      v-else
      v-for="item in card.items"
      :key="item.id"
      :item="item"
    />
  </div>
</template>
