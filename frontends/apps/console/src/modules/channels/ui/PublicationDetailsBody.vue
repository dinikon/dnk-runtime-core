<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty";
import type { PublicationCard } from "../model/publication.types";
import PublicationPositionsTable from "./PublicationPositionsTable.vue";
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
  <div class="flex min-h-60 min-w-0 flex-1 flex-col gap-3 lg:min-h-0">
    <Alert v-if="error" variant="destructive" class="shrink-0"
      ><AlertDescription class="flex flex-wrap items-center gap-3"
        >{{ error
        }}<Button type="button" variant="outline" @click="emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <div
      v-if="pending && !card"
      role="status"
      aria-label="Загрузка публикации"
      class="flex flex-col gap-2"
    >
      <Skeleton v-for="index in 4" :key="index" class="h-10 w-full" />
    </div>
    <section
      v-else-if="card"
      :aria-label="hasVariants ? 'Варианты' : 'Позиция публикации'"
      class="flex min-h-0 min-w-0 flex-1 flex-col"
    >
      <PublicationPositionsTable
        v-if="card.items.length"
        :card="card"
        :requested-publication-id="requestedPublicationId"
        class="max-h-[65dvh] lg:max-h-none"
      />
      <Empty v-else class="flex-1"
        ><EmptyHeader
          ><EmptyTitle>Позиции ещё не получены</EmptyTitle
          ><EmptyDescription
            >Разновидности этой карточки ещё не получены. Обновите публикации в
            подключении.</EmptyDescription
          ></EmptyHeader
        ></Empty
      >
    </section>
  </div>
</template>
