<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CirclePlus, RefreshCw, TriangleAlert, CircleX } from "@lucide/vue";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { importStatusLabels } from "../../model/import.constants";
import type { CatalogImportRun } from "../../model/import.types";
defineProps<{ items: CatalogImportRun[] }>();
defineEmits<{ open: [id: string] }>();
const results = [
  { key: "created", label: "Создано", icon: CirclePlus, color: "text-success" },
  { key: "updated", label: "Обновлено", icon: RefreshCw, color: "text-info" },
  {
    key: "warnings",
    label: "Предупреждений",
    icon: TriangleAlert,
    color: "text-warning",
  },
  { key: "errors", label: "Ошибок", icon: CircleX, color: "text-destructive" },
] as const;
</script>
<template>
  <TooltipProvider :delay-duration="150">
    <div class="overflow-auto rounded-lg border">
      <Table
        ><TableHeader
          ><TableRow
            ><TableHead>Источник</TableHead><TableHead>Статус</TableHead
            ><TableHead>Обработано</TableHead><TableHead>Результат</TableHead
            ><TableHead>Создан</TableHead></TableRow
          ></TableHeader
        ><TableBody>
          <TableRow v-for="run in items" :key="run.id"
            ><TableCell
              ><Button
                variant="link"
                class="h-auto max-w-72 justify-start truncate p-0"
                @click="$emit('open', run.id)"
                >{{ run.name }}</Button
              ></TableCell
            ><TableCell
              ><Badge variant="secondary">{{
                importStatusLabels[run.status]
              }}</Badge></TableCell
            ><TableCell class="tabular-nums"
              >{{ run.processed }} / {{ run.total }}</TableCell
            ><TableCell>
              <div
                class="grid grid-cols-4 items-center gap-3 whitespace-nowrap text-sm tabular-nums"
                aria-label="Результат импорта"
              >
                <Tooltip v-for="result in results" :key="result.key">
                  <TooltipTrigger as-child>
                    <span
                      tabindex="0"
                      role="img"
                      :aria-label="`${result.label}: ${run[result.key]}`"
                      class="inline-flex items-center gap-1.5 rounded-sm outline-offset-4 focus-visible:outline-2 focus-visible:outline-ring"
                    >
                      <component
                        :is="result.icon"
                        class="size-4 shrink-0"
                        :class="result.color"
                        aria-hidden="true"
                      />
                      <span aria-hidden="true">{{ run[result.key] }}</span>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent
                    >{{ result.label }}: {{ run[result.key] }}</TooltipContent
                  >
                </Tooltip>
              </div> </TableCell
            ><TableCell
              class="whitespace-nowrap text-sm text-muted-foreground"
              >{{ run.createdAt.toLocaleString() }}</TableCell
            ></TableRow
          >
        </TableBody></Table
      >
    </div>
  </TooltipProvider>
</template>
