<script setup lang="ts">
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import type { Channel, Platform } from "../model/channels.types";
import ChannelStatusBadge from "./ChannelStatusBadge.vue";
defineProps<{ items: Channel[]; platforms: Platform[] }>();
defineEmits<{ open: [channel: Channel] }>();
</script>
<template>
  <Table
    ><TableHeader
      ><TableRow
        ><TableHead>Канал</TableHead><TableHead>Платформа</TableHead
        ><TableHead>Подключение</TableHead
        ><TableHead>Исходящая синхронизация</TableHead
        ><TableHead><span class="sr-only">Действия</span></TableHead></TableRow
      ></TableHeader
    ><TableBody
      ><TableRow v-for="channel in items" :key="channel.id"
        ><TableCell
          ><Button
            variant="link"
            class="h-auto max-w-64 justify-start whitespace-normal p-0 text-left"
            @click="$emit('open', channel)"
            >{{ channel.name }}</Button
          ></TableCell
        ><TableCell>{{
          platforms.find((p) => p.kind === channel.platformKind)?.label ??
          channel.platformKind
        }}</TableCell
        ><TableCell
          ><ChannelStatusBadge
            :status="channel.verificationStatus"
            :paused="channel.isPaused"
            :archived="channel.isArchived" /></TableCell
        ><TableCell
          ><span class="text-muted-foreground">{{
            channel.isEnabled
              ? "Разрешена · отправка ещё не реализована"
              : "Выключена"
          }}</span></TableCell
        ><TableCell
          ><Button
            variant="outline"
            size="sm"
            @click="$emit('open', channel)"
            >{{
              channel.connectionId ? "Открыть" : "Настроить подключение"
            }}</Button
          ></TableCell
        ></TableRow
      ></TableBody
    ></Table
  >
</template>
