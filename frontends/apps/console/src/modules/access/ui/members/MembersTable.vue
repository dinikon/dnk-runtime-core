<script setup lang="ts">
import {
  Cloud,
  CloudOff,
  RotateCcw,
  ShieldCheck,
  UserMinus,
} from "@lucide/vue";

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
  "change-role": [member: Member];
  "change-status": [member: Member];
}>();

function roleLabel(role: Member["role"]) {
  return role === "admin" ? "Администратор" : "Участник";
}
</script>

<template>
  <div class="overflow-x-auto rounded-lg border">
    <Table class="min-w-[980px]">
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
            <div class="flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                @click="$emit('change-role', member)"
              >
                <ShieldCheck />
                Изменить роль
              </Button>
              <Button
                :variant="
                  member.status === 'active' ? 'destructive' : 'outline'
                "
                size="sm"
                @click="$emit('change-status', member)"
              >
                <UserMinus v-if="member.status === 'active'" />
                <RotateCcw v-else />
                {{ member.status === "active" ? "Уволить" : "Восстановить" }}
              </Button>
            </div>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </div>
</template>
