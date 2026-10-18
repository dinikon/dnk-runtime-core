<script setup lang="ts">
import { useRoute } from "vue-router";
import { useChannelsContext } from "../model/use-channels-context";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
const context = useChannelsContext(),
  route = useRoute();
</script>
<template>
  <RouterView
    v-if="context.enabled.value"
    :key="context.scope.value + String(route.params.channelId ?? 'list')"
  /><Alert v-else
    ><AlertTitle>Рабочее пространство недоступно</AlertTitle
    ><AlertDescription
      >Ожидаем подтверждение организации и текущей сессии.</AlertDescription
    ></Alert
  >
</template>
