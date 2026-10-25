<script setup lang="ts">
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
defineProps<{
  open: boolean;
  pending?: boolean;
  message?: string;
  save?: boolean;
}>();
defineEmits<{ stay: []; discard: []; save: [] }>();
</script>
<template>
  <AlertDialog :open="open"
    ><AlertDialogContent
      ><AlertDialogHeader
        ><AlertDialogTitle>Несохранённые изменения</AlertDialogTitle
        ><AlertDialogDescription>{{
          message ??
          "Вы можете сохранить изменения, отбросить их или остаться на странице."
        }}</AlertDialogDescription></AlertDialogHeader
      ><AlertDialogFooter
        ><Button variant="outline" :disabled="pending" @click="$emit('stay')"
          >Остаться</Button
        ><Button
          variant="secondary"
          :disabled="pending"
          @click="$emit('discard')"
          >{{ message ? "Продолжить" : "Отбросить изменения" }}</Button
        ><Button v-if="save" :disabled="pending" @click="$emit('save')"
          >Сохранить</Button
        ></AlertDialogFooter
      ></AlertDialogContent
    ></AlertDialog
  >
</template>
