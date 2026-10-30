<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useChannelEditor } from "../model/use-channel-editor";
import { useChannelEditorNavigation } from "../model/use-channel-editor-navigation";
import { channelListReturnTo } from "../model/channel-navigation";
import { channelErrorMessage } from "../model/channel.errors";
import ChannelForm from "../ui/ChannelForm.vue";
import ChannelHeader from "../ui/ChannelHeader.vue";
const route = useRoute(),
  router = useRouter();
const editor = useChannelEditor(computed(() => ""));
useChannelEditorNavigation(editor.dirty, editor.busy);
const returnTo = computed(() => channelListReturnTo(route.query.returnTo));
async function save(): Promise<void> {
  const id = await editor.save();
  if (id)
    await router.replace({
      name: "channel-detail",
      params: { id },
      query: { returnTo: returnTo.value },
    });
}
</script>
<template>
  <div class="min-h-0 flex-1 overflow-y-auto">
    <Teleport to="#workspace-page-header" defer
      ><ChannelHeader title="Подключить магазин" @back="router.push(returnTo)"
    /></Teleport>
    <div class="mx-auto w-full max-w-xl pb-4">
      <h1 class="px-4 py-3 text-2xl font-semibold">Подключить магазин</h1>
      <Skeleton v-if="editor.platforms.isPending.value" class="h-64 w-full" />
      <Alert v-else-if="editor.platforms.isError.value" variant="destructive"
        ><AlertDescription
          >{{ channelErrorMessage(editor.platforms.error.value)
          }}<Button variant="outline" @click="editor.platforms.refetch()"
            >Повторить</Button
          ></AlertDescription
        ></Alert
      >
      <ChannelForm
        v-else-if="editor.draft.value && editor.platform.value"
        :draft="editor.draft.value"
        :platform="editor.platform.value"
        :platforms="editor.platforms.data.value ?? []"
        :editing="false"
        :busy="editor.busy.value"
        @change="editor.draft.value = $event"
        @platform="editor.changePlatform"
        @submit="save"
      >
        <template #messages
          ><Alert v-if="editor.error.value" variant="destructive"
            ><AlertDescription>{{
              editor.error.value
            }}</AlertDescription></Alert
          ></template
        >
      </ChannelForm>
    </div>
  </div>
</template>
