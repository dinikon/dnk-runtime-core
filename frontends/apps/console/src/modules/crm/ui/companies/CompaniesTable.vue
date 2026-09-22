<script setup lang="ts">
import { MoreHorizontal } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Company } from "../../model/crm.types";

defineProps<{ items: Company[] }>();
defineEmits<{ edit: [item: Company]; delete: [item: Company] }>();

function formatDate(value: string) {
  return new Date(value).toLocaleString("uk-UA");
}
</script>

<template>
  <div class="w-full min-w-0 overflow-x-auto rounded-lg border bg-background">
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Название</TableHead>
          <TableHead>Создана</TableHead>
          <TableHead>Обновлена</TableHead>
          <TableHead><span class="sr-only">Действия</span></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="item in items" :key="item.id">
          <TableCell class="font-medium">{{ item.name }}</TableCell>
          <TableCell>{{ formatDate(item.createdAt) }}</TableCell>
          <TableCell>{{ formatDate(item.updatedAt) }}</TableCell>
          <TableCell class="text-right">
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Действия компании"
                >
                  <MoreHorizontal />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuGroup>
                  <DropdownMenuItem @click="$emit('edit', item)">
                    Редактировать
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    variant="destructive"
                    @click="$emit('delete', item)"
                  >
                    Удалить
                  </DropdownMenuItem>
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </div>
</template>
