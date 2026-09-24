<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Member, Role } from "../../model/access.types";

const props = defineProps<{
  open: boolean;
  member: Member | null;
  pending: boolean;
  error: string;
  onlyActiveAdmin: boolean;
}>();
const emit = defineEmits<{
  "update:open": [value: boolean];
  save: [role: Role];
}>();

const role = ref<Role>("member");

watch(
  () => [props.open, props.member] as const,
  () => {
    if (!props.open || !props.member) return;
    role.value = props.member.role;
  },
  { immediate: true },
);

const removesLastAdmin = computed(
  () =>
    Boolean(props.member) &&
    props.onlyActiveAdmin &&
    props.member?.role === "admin" &&
    props.member.status === "active" &&
    role.value !== "admin",
);
const unchanged = computed(() => role.value === props.member?.role);

function submit() {
  if (!props.member || removesLastAdmin.value || unchanged.value) return;
  emit("save", role.value);
}

function updateOpen(value: boolean) {
  if (!value && props.pending) return;
  emit("update:open", value);
}
</script>

<template>
  <Dialog :open="open" @update:open="updateOpen">
    <DialogContent :show-close-button="!pending">
      <DialogHeader>
        <DialogTitle>Изменить роль</DialogTitle>
        <DialogDescription v-if="member">
          {{ member.displayName }} · {{ member.email }}
        </DialogDescription>
      </DialogHeader>
      <FieldGroup>
        <Field :data-invalid="removesLastAdmin">
          <FieldLabel for="member-role">Роль</FieldLabel>
          <Select v-model="role" :disabled="pending">
            <SelectTrigger id="member-role" :aria-invalid="removesLastAdmin">
              <SelectValue />
            </SelectTrigger>
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
      </FieldGroup>
      <Alert v-if="removesLastAdmin" variant="destructive">
        <AlertDescription>
          Нельзя понизить роль последнего активного администратора.
        </AlertDescription>
      </Alert>
      <Alert v-if="error" variant="destructive">
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>
      <DialogFooter>
        <Button
          variant="outline"
          :disabled="pending"
          @click="emit('update:open', false)"
        >
          Отмена
        </Button>
        <Button
          :disabled="pending || removesLastAdmin || unchanged"
          @click="submit"
        >
          {{ pending ? "Сохраняем…" : "Сохранить роль" }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
