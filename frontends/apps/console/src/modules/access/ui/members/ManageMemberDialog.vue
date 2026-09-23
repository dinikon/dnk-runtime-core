<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  Member,
  MemberStatus,
  MemberUpdate,
  Role,
} from "../../model/access.types";

const props = defineProps<{
  open: boolean;
  member: Member | null;
  pending: boolean;
  error: string;
  onlyActiveAdmin: boolean;
}>();
const emit = defineEmits<{
  "update:open": [value: boolean];
  save: [update: MemberUpdate];
}>();

const role = ref<Role>("member");
const status = ref<MemberStatus>("active");
const confirmRevokeOpen = ref(false);

watch(
  () => [props.open, props.member] as const,
  () => {
    if (!props.open || !props.member) return;
    role.value = props.member.role;
    status.value = props.member.status;
    confirmRevokeOpen.value = false;
  },
  { immediate: true },
);

const removesLastAdmin = computed(
  () =>
    Boolean(props.member) &&
    props.onlyActiveAdmin &&
    props.member?.role === "admin" &&
    props.member.status === "active" &&
    (role.value !== "admin" || status.value !== "active"),
);
const unchanged = computed(
  () =>
    role.value === props.member?.role && status.value === props.member?.status,
);

function submit() {
  if (!props.member || removesLastAdmin.value || unchanged.value) return;
  if (props.member.status === "active" && status.value === "revoked") {
    confirmRevokeOpen.value = true;
    return;
  }
  emit("save", { role: role.value, status: status.value });
}

function confirmRevoke() {
  confirmRevokeOpen.value = false;
  emit("save", { role: role.value, status: status.value });
}
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Управление доступом</DialogTitle>
        <DialogDescription v-if="member">
          {{ member.displayName }} · {{ member.email }}
        </DialogDescription>
      </DialogHeader>
      <div class="grid gap-5 py-2">
        <Field>
          <FieldLabel for="member-role">Роль</FieldLabel>
          <Select v-model="role" :disabled="pending">
            <SelectTrigger id="member-role"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="member">Участник</SelectItem>
                <SelectItem value="admin">Администратор</SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>
          <FieldDescription>
            Администратор может управлять пользователями и настройками.
          </FieldDescription>
        </Field>
        <Field>
          <FieldLabel for="member-status">Доступ</FieldLabel>
          <Select v-model="status" :disabled="pending">
            <SelectTrigger id="member-status"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="active">Активен</SelectItem>
                <SelectItem value="revoked">Отозван</SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>
          <FieldDescription>
            Отзыв доступа завершит активные сессии пользователя.
          </FieldDescription>
        </Field>
        <Alert v-if="removesLastAdmin" variant="destructive">
          <AlertDescription>
            Нельзя понизить роль или отозвать доступ у последнего активного
            администратора.
          </AlertDescription>
        </Alert>
        <Alert v-if="error" variant="destructive">
          <AlertDescription>{{ error }}</AlertDescription>
        </Alert>
      </div>
      <DialogFooter>
        <Button variant="outline" @click="emit('update:open', false)">
          Отмена
        </Button>
        <Button
          :disabled="pending || removesLastAdmin || unchanged"
          @click="submit"
        >
          {{ pending ? "Сохраняем…" : "Сохранить" }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>

  <AlertDialog v-model:open="confirmRevokeOpen">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>Отозвать доступ?</AlertDialogTitle>
        <AlertDialogDescription>
          Пользователь потеряет доступ к рабочему пространству, а его активные
          сессии будут завершены.
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel>Отмена</AlertDialogCancel>
        <AlertDialogAction
          class="bg-destructive text-white"
          @click="confirmRevoke"
        >
          Отозвать доступ
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
