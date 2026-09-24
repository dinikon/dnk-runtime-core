<script setup lang="ts">
import { computed } from "vue";

import type { Member, MemberStatus } from "../../model/access.types";
import ConfirmAccessActionDialog from "../common/ConfirmAccessActionDialog.vue";

const props = defineProps<{
  open: boolean;
  member: Member | null;
  pending: boolean;
  error: string;
  onlyActiveAdmin: boolean;
}>();
const emit = defineEmits<{
  "update:open": [value: boolean];
  confirm: [status: MemberStatus];
}>();

const isRevoking = computed(() => props.member?.status === "active");
const nextStatus = computed<MemberStatus>(() =>
  isRevoking.value ? "revoked" : "active",
);
const title = computed(() =>
  isRevoking.value ? "Уволить пользователя?" : "Восстановить пользователя?",
);
const description = computed(() => {
  const identity = props.member
    ? `${props.member.displayName} · ${props.member.email}. `
    : "";
  return isRevoking.value
    ? `${identity}Пользователь потеряет доступ к рабочему пространству, а его активные сессии будут завершены.`
    : `${identity}Пользователь снова сможет войти в рабочее пространство.`;
});
</script>

<template>
  <ConfirmAccessActionDialog
    :open="open"
    :title="title"
    :description="description"
    :action-label="isRevoking ? 'Уволить' : 'Восстановить'"
    :action-variant="isRevoking ? 'destructive' : 'default'"
    :action-disabled="isRevoking && onlyActiveAdmin"
    :blocked-message="
      isRevoking && onlyActiveAdmin
        ? 'Нельзя уволить последнего активного администратора.'
        : ''
    "
    :pending="pending"
    :error="error"
    @update:open="emit('update:open', $event)"
    @confirm="emit('confirm', nextStatus)"
  />
</template>
