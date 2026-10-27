<script setup lang="ts">
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import ChannelStatus from "./ChannelStatus.vue";
import type { Channel, Platform } from "../model/channel.types";
defineProps<{ items: Channel[]; platforms: Platform[] }>();
const emit = defineEmits<{ open: [id: string] }>();
</script>
<template>
  <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
    <Card v-for="channel in items" :key="channel.id"
      ><CardHeader
        ><CardTitle class="truncate">{{ channel.name }}</CardTitle
        ><CardDescription>{{
          platforms.find((p) => p.kind === channel.platformKind)?.title ??
          channel.platformKind
        }}</CardDescription></CardHeader
      ><CardContent class="flex flex-col gap-3"
        ><ChannelStatus :channel="channel" />
        <p class="break-all text-sm text-muted-foreground">
          {{ channel.identity?.key ?? channel.config.endpoint }}
        </p></CardContent
      ><CardFooter
        ><Button variant="outline" @click="emit('open', channel.id)"
          >Открыть канал</Button
        ></CardFooter
      ></Card
    >
  </div>
</template>
