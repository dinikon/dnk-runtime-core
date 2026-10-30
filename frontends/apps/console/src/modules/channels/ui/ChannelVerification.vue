<script setup lang="ts">
import { Button } from "@/components/ui/button";
import type { Channel } from "../model/channel.types";
import { shouldPoll } from "../model/channel.schema";
import { channelErrorMessage } from "../model/channel.errors";
import ChannelStatus from "./ChannelStatus.vue";
defineProps<{ channel: Channel; busy: boolean; dirty: boolean }>();
defineEmits<{ verify: [] }>();
</script>
<template>
  <div class="flex flex-col items-start gap-3">
    <ChannelStatus :channel="channel" />
    <p
      v-if="channel.verification.checkedAt"
      class="text-xs text-muted-foreground"
    >
      Проверено:
      {{ new Date(channel.verification.checkedAt).toLocaleString("ru-RU") }}
    </p>
    <p class="break-all text-sm text-muted-foreground">
      {{
        channel.identity
          ? "Магазин: " + channel.identity.key
          : "Магазин ещё не подтверждён."
      }}
    </p>
    <p v-if="channel.recoveryRequired" role="status" class="text-sm">
      Проверка прервана. Запустите её снова.
    </p>
    <p
      v-else-if="channel.verification.errorCode"
      role="status"
      class="text-sm text-destructive"
    >
      {{ channelErrorMessage(channel.verification.errorCode) }}
    </p>
    <Button
      type="button"
      variant="outline"
      :disabled="
        busy ||
        dirty ||
        shouldPoll(channel) ||
        !channel.availableCapabilities.includes('verify_connection')
      "
      @click="$emit('verify')"
      >Проверить подключение</Button
    >
    <p v-if="dirty" class="text-xs text-muted-foreground">
      Сначала сохраните изменения формы.
    </p>
  </div>
</template>
