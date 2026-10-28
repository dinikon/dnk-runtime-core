<script setup lang="ts">
import { Badge } from "@/components/ui/badge";
import type { Channel } from "../model/channel.types";
defineProps<{ channel: Channel }>();
</script>
<template>
  <Badge
    :variant="
      channel.recoveryRequired || channel.verification.status === 'error'
        ? 'destructive'
        : channel.verification.status === 'verified'
          ? 'default'
          : 'secondary'
    "
    >{{
      channel.recoveryRequired
        ? "Проверка прервана"
        : channel.verification.status === "pending"
          ? "Проверяем подключение"
          : channel.verification.status === "verified"
            ? "Подключение проверено"
            : "Ошибка проверки"
    }}</Badge
  >
</template>
