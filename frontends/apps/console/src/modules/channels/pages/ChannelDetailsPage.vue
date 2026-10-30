<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Radio } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useChannelEditor } from "../model/use-channel-editor";
import { useChannelEditorNavigation } from "../model/use-channel-editor-navigation";
import { channelListReturnTo } from "../model/channel-navigation";
import { channelErrorMessage } from "../model/channel.errors";
import ChannelHeader from "../ui/ChannelHeader.vue";
import ChannelForm from "../ui/ChannelForm.vue";
import DeleteChannelDialog from "../ui/DeleteChannelDialog.vue";
import ChannelPublicationsPage from "./ChannelPublicationsPage.vue";
const route = useRoute(),
  router = useRouter();
const id = computed(() => String(route.params.id ?? ""));
const editor = useChannelEditor(id);
const deleteOpen = ref(false);
watch(editor.contextKey, () => {
  deleteOpen.value = false;
});
useChannelEditorNavigation(editor.dirty, editor.busy);
const returnTo = computed(() => channelListReturnTo(route.query.returnTo));
const loading = computed(
  () => editor.query.isPending.value || editor.platforms.isPending.value,
);
const loadError = computed(() =>
  editor.query.error.value || editor.platforms.error.value
    ? channelErrorMessage(
        editor.query.error.value ?? editor.platforms.error.value,
      )
    : editor.query.data.value &&
        editor.platforms.data.value &&
        !editor.platform.value
      ? "Платформа этого подключения сейчас недоступна."
      : "",
);
async function remove(): Promise<void> {
  if (await editor.remove()) {
    deleteOpen.value = false;
    await router.push(returnTo.value);
  }
}
</script>
<template>
  <div
    class="channel-workspace -mx-4 -mb-4 min-h-0 min-w-0 flex-1 overflow-y-auto bg-background lg:overflow-hidden"
  >
    <Teleport to="#workspace-page-header" defer
      ><ChannelHeader
        :title="editor.query.data.value?.name ?? 'Подключение'"
        :removable="!!editor.query.data.value"
        :busy="editor.busy.value"
        @back="router.push(returnTo)"
        @remove="deleteOpen = true"
    /></Teleport>
    <section
      class="channel-workspace-fields"
      aria-label="Настройки подключения"
    >
      <div
        v-if="loading && !editor.draft.value"
        role="status"
        aria-label="Загрузка подключения"
        class="p-4"
      >
        <Skeleton class="h-96 w-full" />
      </div>
      <ChannelForm
        v-if="editor.draft.value && editor.platform.value"
        :key="editor.contextKey.value"
        :draft="editor.draft.value"
        :platform="editor.platform.value"
        :platforms="editor.platforms.data.value ?? []"
        :channel="editor.query.data.value"
        editing
        :busy="editor.busy.value"
        :dirty="editor.dirty.value"
        @change="editor.draft.value = $event"
        @submit="editor.save"
        @verify="editor.verify"
      >
        <template #messages>
          <Alert v-if="loadError" variant="destructive" class="mt-3"
            ><AlertDescription
              >{{ loadError
              }}<Button
                type="button"
                variant="outline"
                @click="
                  editor.query.refetch();
                  editor.platforms.refetch();
                "
                >Повторить</Button
              ></AlertDescription
            ></Alert
          >
          <Alert v-if="editor.error.value" variant="destructive" class="mt-3"
            ><AlertDescription>{{
              editor.error.value
            }}</AlertDescription></Alert
          >
          <Alert
            v-if="
              editor.query.data.value &&
              editor.baseRevision.value !== editor.query.data.value.revision
            "
            class="mt-3"
            ><AlertDescription class="flex flex-col gap-3"
              >Сохранённое подключение изменилось. Ваш черновик сохранён.<Button
                type="button"
                variant="outline"
                class="whitespace-normal"
                :disabled="editor.busy.value"
                @click="editor.resetDraft"
                >Загрузить актуальные настройки</Button
              ><Button
                type="button"
                variant="outline"
                class="whitespace-normal"
                :disabled="editor.busy.value"
                @click="
                  editor.baseRevision.value = editor.query.data.value.revision
                "
                >Применить черновик к актуальной версии</Button
              ></AlertDescription
            ></Alert
          >
        </template>
      </ChannelForm>
      <Alert v-else-if="loadError" variant="destructive" class="m-4"
        ><AlertDescription
          >{{ loadError
          }}<Button
            variant="outline"
            @click="
              editor.query.refetch();
              editor.platforms.refetch();
            "
            >Повторить</Button
          ></AlertDescription
        ></Alert
      >
    </section>
    <Tabs
      default-value="publications"
      class="channel-workspace-publications flex min-w-0 flex-col gap-0"
    >
      <TabsList
        variant="line"
        aria-label="Разделы подключения"
        class="shrink-0 border-b px-4"
        ><TabsTrigger value="publications" variant="line"
          ><Radio
            class="mr-2 size-4"
            aria-hidden="true"
          />Публикации</TabsTrigger
        ></TabsList
      >
      <TabsContent
        value="publications"
        class="flex min-h-0 flex-1 flex-col p-4 lg:p-6"
      >
        <ChannelPublicationsPage v-if="editor.query.data.value" />
        <Skeleton v-else-if="loading" class="h-72 w-full" />
      </TabsContent>
    </Tabs>
    <DeleteChannelDialog
      v-if="editor.query.data.value"
      v-model:open="deleteOpen"
      :name="editor.query.data.value.name"
      :busy="editor.busy.value"
      :error="editor.deleteError.value"
      @confirm="remove"
    />
  </div>
</template>
