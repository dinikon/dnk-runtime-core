<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { Plus } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useChannelsContext } from "../model/use-channels-context";
import { useChannelsPageState } from "../model/use-channels-page-state";
import { useChannelsQuery } from "../model/queries/use-channels-query";
import { usePlatformsQuery } from "../model/queries/use-platforms-query";
import { useCreateChannel } from "../model/mutations/use-create-channel";
import { channelErrorMessage } from "../model/channels.errors";
import type { Channel, CreateChannelInput } from "../model/channels.types";
import ChannelsQueryBody from "../ui/ChannelsQueryBody.vue";
import ChannelsList from "../ui/ChannelsList.vue";
import ChannelsPagination from "../ui/ChannelsPagination.vue";
import CreateChannelDialog from "../ui/CreateChannelDialog.vue";
const context = useChannelsContext(),
  state = useChannelsPageState(),
  router = useRouter();
const channels = useChannelsQuery(context, state.listFilters),
  platforms = usePlatformsQuery(context),
  create = useCreateChannel(context);
const dialogOpen = ref(false),
  createError = ref<string | null>(null);
const listError = computed(() =>
  channels.error.value ? channelErrorMessage(channels.error.value) : null,
);
function open(channel: Channel): void {
  void router.push({
    name: "channel-detail",
    params: { channelId: channel.id },
    query: channel.connectionId ? {} : { tab: "connection" },
  });
}
function close(): void {
  if (!create.isPending.value) {
    dialogOpen.value = false;
    createError.value = null;
    create.reset();
  }
}
async function submit(input: CreateChannelInput): Promise<void> {
  if (create.isPending.value) return;
  const current = context.capture();
  createError.value = null;
  try {
    const result = await create.mutateAsync(input);
    if (current()) {
      dialogOpen.value = false;
      await router.push({
        name: "channel-detail",
        params: { channelId: result.id },
        query: { tab: "connection" },
      });
    }
  } catch (error: unknown) {
    if (current()) createError.value = channelErrorMessage(error);
  } finally {
    create.reset();
  }
}
</script>
<template>
  <main class="flex min-h-0 flex-1 flex-col gap-6 overflow-auto">
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Каналы</h1>
        <p class="text-muted-foreground mt-1 text-sm">
          Магазины и источники продаж. У каждого канала одно подключение.
        </p>
      </div>
      <Button
        :disabled="platforms.isPending.value || !platforms.data.value?.length"
        @click="dialogOpen = true"
        ><Plus data-icon="inline-start" />Добавить канал</Button
      >
    </header>
    <Alert v-if="platforms.error.value" variant="destructive"
      ><AlertDescription
        >{{ channelErrorMessage(platforms.error.value)
        }}<Button variant="outline" size="sm" @click="platforms.refetch()"
          >Повторить загрузку платформ</Button
        ></AlertDescription
      ></Alert
    ><ChannelsQueryBody
      :pending="channels.isPending.value"
      :error="listError"
      :has-data="!!channels.data.value"
      :empty="!channels.data.value?.items.length"
      empty-title="Каналов пока нет"
      empty-description="Добавьте канал, чтобы подключить магазин и загрузить его публикации."
      @retry="channels.refetch()"
      ><ChannelsList
        :items="channels.data.value?.items ?? []"
        :platforms="platforms.data.value ?? []"
        @open="open" /></ChannelsQueryBody
    ><ChannelsPagination
      v-if="channels.data.value"
      :page="state.page.value"
      :total="channels.data.value.total"
      :limit="20"
      :pending="channels.isFetching.value"
      @change="state.setPage"
    /><CreateChannelDialog
      v-if="dialogOpen"
      :open="dialogOpen"
      :platforms="platforms.data.value ?? []"
      :pending="create.isPending.value"
      :error="createError"
      @close="close"
      @submit="submit"
    />
  </main>
</template>
