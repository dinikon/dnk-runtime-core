<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
</script>
<template>
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
          ><TableCell class="min-w-52 text-sm text-muted-foreground"
            >Создано {{ run.created }} · Обновлено {{ run.updated }}
            <p v-if="run.errors || run.warnings">
              Ошибок {{ run.errors }} · Предупреждений {{ run.warnings }}
            </p></TableCell
          ><TableCell class="whitespace-nowrap text-sm text-muted-foreground">{{
            run.createdAt.toLocaleString()
          }}</TableCell></TableRow
        >
      </TableBody></Table
    >
  </div>
</template>
