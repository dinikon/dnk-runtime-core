<script setup lang="ts">
import { Cloud, CloudOff, Settings2 } from "@lucide/vue";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Member } from "../../model/access.types";

defineProps<{
  items: Member[];
}>();
defineEmits<{
  manage: [member: Member];
}>();

function roleLabel(role: Member["role"]) {
  return role === "admin" ? "Администратор" : "Участник";
}
</script>

<template>
  <div class="overflow-x-auto rounded-lg border">
    <Table class="min-w-[820px]">
      <TableHeader>
        <TableRow>
          <TableHead>Пользователь</TableHead>
          <TableHead>Роль</TableHead>
          <TableHead>Статус</TableHead>
          <TableHead>Связь с облаком</TableHead>
          <TableHead class="text-right">Действия</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="member in items" :key="member.id">
          <TableCell>
            <div class="flex items-center gap-3">
              <Avatar class="size-9">
                <AvatarFallback>{{ member.initials }}</AvatarFallback>
              </Avatar>
              <div class="min-w-0">
                <p class="truncate font-medium">{{ member.displayName }}</p>
                <p class="truncate text-sm text-muted-foreground">
                  {{ member.email }}
                </p>
              </div>
            </div>
          </TableCell>
          <TableCell>{{ roleLabel(member.role) }}</TableCell>
          <TableCell>
            <Badge
              :variant="member.status === 'active' ? 'secondary' : 'outline'"
            >
              {{ member.status === "active" ? "Активен" : "Доступ отозван" }}
            </Badge>
          </TableCell>
          <TableCell>
            <span class="inline-flex items-center gap-2 text-sm">
              <Cloud
                v-if="member.cloudLinked"
                class="size-4 text-emerald-600"
              />
              <CloudOff v-else class="size-4 text-muted-foreground" />
              {{ member.cloudLinked ? "Подключено" : "Не подключено" }}
            </span>
          </TableCell>
          <TableCell class="text-right">
            <Button
              variant="outline"
              size="sm"
              @click="$emit('manage', member)"
            >
              <Settings2 />
              Управление доступом
            </Button>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </div>
</template>
