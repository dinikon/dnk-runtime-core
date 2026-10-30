<script setup lang="ts">
import { MoreHorizontal, ExternalLink } from "@lucide/vue";
import { DataTable } from "@/components/custom-ui/data-table";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import type { Channel, Platform } from "../model/channel.types";
import ChannelStatus from "./ChannelStatus.vue";
import { channelsColumns } from "./channels.columns";
defineProps<{ items: Channel[]; platforms: Platform[] }>();
const emit = defineEmits<{ open: [id: string] }>();
</script>
<template>
  <DataTable
    :rows="items"
    :columns="channelsColumns"
    :row-key="(row) => row.id"
    caption="Подключения"
    class="max-h-[65dvh] lg:max-h-none"
    @row-activate="emit('open', $event.id)"
  >
    <template #header="{ column }">
      <span v-if="column.key === 'actions'" class="sr-only">{{
        column.label
      }}</span>
      <template v-else>{{ column.label }}</template>
    </template>
    <template #cell="{ row, column }">
      <button
        v-if="column.key === 'name'"
        type="button"
        class="block w-full truncate text-left font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        :title="row.name"
        @click="emit('open', row.id)"
      >
        {{ row.name }}
      </button>
      <span v-else-if="column.key === 'platform'" class="block truncate">{{
        platforms.find((p) => p.kind === row.platformKind)?.title ??
        row.platformKind
      }}</span>
      <span
        v-else-if="column.key === 'endpoint'"
        class="block truncate text-muted-foreground"
        :title="row.config.endpoint"
        >{{ row.config.endpoint }}</span
      >
      <ChannelStatus v-else-if="column.key === 'status'" :channel="row" />
      <span
        v-else-if="column.key === 'checked'"
        class="whitespace-nowrap text-muted-foreground"
        >{{
          row.verification.checkedAt
            ? new Date(row.verification.checkedAt).toLocaleString("ru-RU")
            : "—"
        }}</span
      >
      <DropdownMenu v-else-if="column.key === 'actions'">
        <DropdownMenuTrigger as-child
          ><Button
            variant="ghost"
            size="icon-sm"
            :aria-label="`Действия: ${row.name}`"
            ><MoreHorizontal /></Button
        ></DropdownMenuTrigger>
        <DropdownMenuContent align="end"
          ><DropdownMenuGroup
            ><DropdownMenuItem @select="emit('open', row.id)"
              ><ExternalLink />Открыть подключение</DropdownMenuItem
            ></DropdownMenuGroup
          ></DropdownMenuContent
        >
      </DropdownMenu>
    </template>
  </DataTable>
</template>
