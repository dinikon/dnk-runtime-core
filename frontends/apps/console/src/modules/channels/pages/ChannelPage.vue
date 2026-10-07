<script setup lang="ts">
import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQueryClient } from "@tanstack/vue-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useChannel,
  useChannelTenant,
  usePublicationImport,
  useKinds,
} from "../model/queries";
const route = useRoute(),
  router = useRouter(),
  client = useQueryClient();
const id = computed(() => String(route.params.channelId ?? ""));
const tenant = useChannelTenant(),
  channel = useChannel(id),
  run = usePublicationImport(id);
const kinds = useKinds();
const platformLabel = computed(
  () =>
    kinds.data.value?.find(
      (platform) => platform.kind === channel.data.value?.kind,
    )?.label ?? channel.data.value?.kind,
);
const tab = computed(() =>
  route.name === "channel-settings" ? "settings" : "publications",
);
watch(
  () => [run.data.value?.id, run.data.value?.pages, run.data.value?.status],
  () => {
    void client.invalidateQueries({
      queryKey: ["channels", tenant.value, "publications", id.value],
    });
  },
);
function navigate(value: string | number) {
  if (value === tab.value) return;
  void router.push(
    `/channels/${id.value}/${value === "settings" ? "settings" : "publications"}`,
  );
}
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex flex-wrap items-center gap-3">
        <h1 class="text-2xl font-semibold">
          {{ channel.data.value?.name ?? "Канал" }}
        </h1>
        <Badge v-if="channel.data.value" variant="secondary">{{
          platformLabel
        }}</Badge>
      </div>
      <Button as-child variant="outline"
        ><RouterLink to="/channels">К каналам</RouterLink></Button
      >
    </header>
    <Skeleton
      v-if="channel.isPending.value"
      class="h-64"
      aria-label="Загрузка канала"
    />
    <Alert v-else-if="channel.isError.value" variant="destructive"
      ><AlertTitle>Не удалось загрузить канал</AlertTitle
      ><AlertDescription
        ><Button variant="outline" @click="channel.refetch()"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <Tabs v-else :model-value="tab" @update:model-value="navigate">
      <TabsList class="flex h-auto w-fit max-w-full flex-wrap">
        <TabsTrigger value="publications">Публикации</TabsTrigger>
        <TabsTrigger value="settings">Настройки подключения</TabsTrigger>
      </TabsList>
      <TabsContent :value="tab"><RouterView :key="id" /></TabsContent>
    </Tabs>
  </div>
</template>
