<script setup lang="ts">
import { Ban } from "@lucide/vue";

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
import type {
  Invitation,
  InvitationState,
  Role,
} from "../../model/access.types";

defineProps<{
  items: Invitation[];
  pending: boolean;
}>();
defineEmits<{
  revoke: [invitation: Invitation];
}>();

const stateLabels: Record<InvitationState, string> = {
  pending: "Ожидает",
  accepted: "Принято",
  revoked: "Отозвано",
  expired: "Истекло",
};

function roleLabel(role: Role) {
  return role === "admin" ? "Администратор" : "Участник";
}
</script>

<template>
  <div class="overflow-x-auto rounded-lg border">
    <Table class="min-w-[720px]">
      <TableHeader>
        <TableRow>
          <TableHead>Email</TableHead>
          <TableHead>Роль</TableHead>
          <TableHead>Статус</TableHead>
          <TableHead>Действует до</TableHead>
          <TableHead class="text-right">Действия</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="invitation in items" :key="invitation.id">
          <TableCell class="font-medium">{{ invitation.email }}</TableCell>
          <TableCell>{{ roleLabel(invitation.role) }}</TableCell>
          <TableCell>
            <Badge
              :variant="
                invitation.state === 'pending' ? 'secondary' : 'outline'
              "
            >
              {{ stateLabels[invitation.state] }}
            </Badge>
          </TableCell>
          <TableCell>
            {{ new Date(invitation.expiresAt).toLocaleDateString("ru-RU") }}
          </TableCell>
          <TableCell class="text-right">
            <Button
              v-if="invitation.state === 'pending'"
              variant="outline"
              size="sm"
              :disabled="pending"
              @click="$emit('revoke', invitation)"
            >
              <Ban />
              Отозвать
            </Button>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </div>
</template>
