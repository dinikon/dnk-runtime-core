<script setup lang="ts">
import { Button } from "@/components/ui/button";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import BindingPositionCell from "./BindingPositionCell.vue";
import type {
  BindingPair,
  BindingPosition,
} from "../../model/bindings/binding.types";
defineProps<{
  catalog: BindingPosition[];
  publications: BindingPosition[];
  items: BindingPair[];
  occupied: string[];
  busy: boolean;
  primaryPublicationId?: string;
  contextPublicationId?: string;
}>();
const emit = defineEmits<{
  pair: [catalogId: string, publicationId: string];
  suggest: [];
}>();
</script>
<template>
  <section class="space-y-3">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h3 class="font-medium">Явное сопоставление позиций</h3>
      <Button
        size="sm"
        variant="outline"
        :disabled="busy"
        @click="emit('suggest')"
        >Применить точные совпадения SKU</Button
      >
    </div>
    <p class="text-sm text-muted-foreground">
      Можно сохранить часть соответствий. В пределах этой группы каждая позиция
      используется один раз.
    </p>
    <p
      v-if="
        primaryPublicationId &&
        !items.some((p) => p.publicationId === primaryPublicationId)
      "
      class="text-muted-foreground text-sm"
    >
      Основная позиция Prom пока не сопоставлена.
    </p>
    <div class="overflow-x-auto">
      <Table class="min-w-[560px]"
        ><TableHeader
          ><TableRow
            ><TableHead>Catalog</TableHead
            ><TableHead>Позиция площадки</TableHead></TableRow
          ></TableHeader
        ><TableBody
          ><TableRow v-for="position in catalog" :key="position.id"
            ><TableCell class="w-1/2"
              ><BindingPositionCell :position="position" /></TableCell
            ><TableCell
              ><select
                class="border-input bg-background h-10 w-full rounded-md border px-2 text-sm"
                :aria-label="`Публикация для ${position.title ?? 'Без названия'} (${position.sku ?? position.id})`"
                :value="
                  items.find((p) => p.catalogId === position.id)
                    ?.publicationId ?? ''
                "
                :disabled="busy"
                @change="
                  emit(
                    'pair',
                    position.id,
                    ($event.target as HTMLSelectElement).value,
                  )
                "
              >
                <option value="">Не сопоставлено</option>
                <option
                  v-for="p in publications"
                  :key="p.id"
                  :value="p.id"
                  :disabled="
                    occupied.includes(p.id) ||
                    items.some(
                      (v) =>
                        v.publicationId === p.id && v.catalogId !== position.id,
                    )
                  "
                >
                  {{ p.id === primaryPublicationId ? "Основная · " : ""
                  }}{{ p.title ?? "Без названия" }} ·
                  {{ p.sku ?? "Без артикула" }} · #{{ p.externalId ?? p.id
                  }}{{
                    p.id === contextPublicationId ? " · Текущая публикация" : ""
                  }}
                </option></select
              ><BindingPositionCell
                v-if="
                  publications.find(
                    (p) =>
                      p.id ===
                      items.find((v) => v.catalogId === position.id)
                        ?.publicationId,
                  )
                "
                class="mt-2"
                :position="
                  publications.find(
                    (p) =>
                      p.id ===
                      items.find((v) => v.catalogId === position.id)
                        ?.publicationId,
                  )!
                "
              />
              <p
                v-else-if="items.some((v) => v.catalogId === position.id)"
                class="mt-2 text-sm text-destructive"
              >
                Позиция отсутствует в текущем снимке.
              </p></TableCell
            ></TableRow
          ></TableBody
        ></Table
      >
    </div>
  </section>
</template>
