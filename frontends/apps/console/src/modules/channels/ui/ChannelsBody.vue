<script setup lang="ts">
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty";
import ChannelList from "./ChannelList.vue";
import type { Channel, Platform } from "../model/channel.types";
defineProps<{
  loading: boolean;
  error: string;
  items: Channel[];
  platforms: Platform[];
}>();
const emit = defineEmits<{ retry: []; open: [id: string] }>();
</script>
<template>
  <Skeleton v-if="loading" class="h-48 w-full" /><template v-else
    ><Alert v-if="error" variant="destructive"
      ><AlertDescription class="flex flex-wrap items-center gap-3"
        >{{ error
        }}<Button variant="outline" @click="emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    ><ChannelList
      v-if="items.length"
      :items="items"
      :platforms="platforms"
      @open="emit('open', $event)"
    /><Empty v-else-if="!error"
      ><EmptyHeader
        ><EmptyTitle>Каналы не найдены</EmptyTitle
        ><EmptyDescription
          >Подключите магазин или измените фильтры.</EmptyDescription
        ></EmptyHeader
      ></Empty
    ></template
  >
</template>
