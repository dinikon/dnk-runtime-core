<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import FeedSections from "../ui/page/FeedSections.vue";
import FeedHeader from "../ui/page/FeedHeader.vue";
import FeedForm from "../ui/forms/FeedForm.vue";
import ArchiveFeedDialog from "../ui/forms/ArchiveFeedDialog.vue";
import FeedStatus from "../ui/item/FeedStatus.vue";
import { useFeedEditor } from "../model/use-feed-editor";
import { useFeedEditorNavigation } from "../model/use-feed-editor-navigation";
import { useArchiveFeed } from "../model/use-archive-feed";
import { feedListReturnTo, feedSectionRoutes } from "../model/feed.navigation";
import { feedErrorMessage } from "../model/feed.errors";
import { FeedApiError, type Feed } from "../model/feed.types";
const route = useRoute(),
  router = useRouter();
const id = computed(() =>
  typeof route.params.id === "string" ? route.params.id : "",
);
const editor = useFeedEditor(id),
  archive = useArchiveFeed(),
  target = ref<Feed | null>(null);
const busy = computed(() => editor.busy.value || archive.pending.value);
useFeedEditorNavigation(editor.dirty, busy);
const returnTo = computed(() => feedListReturnTo(route.query.returnTo));
const queryError = computed(() =>
  editor.query.error.value ? feedErrorMessage(editor.query.error.value) : "",
);
const archiveError = computed(() =>
  archive.error.value ? feedErrorMessage(archive.error.value) : "",
);
const archiveConflict = computed(
  () =>
    archive.error.value instanceof FeedApiError &&
    archive.error.value.status === 409,
);
watch(
  editor.contextKey,
  () => {
    target.value = null;
  },
  { flush: "sync" },
);
function back(): void {
  void router.push(returnTo.value);
}
async function reset(): Promise<void> {
  const context = editor.contextKey.value;
  if (id.value && editor.conflict.value) {
    const result = await editor.query.refetch();
    if (result.isError || context !== editor.contextKey.value) return;
  }
  if (
    !editor.dirty.value ||
    window.confirm("Загрузить актуальные настройки и отменить ваши изменения?")
  )
    editor.reset();
}
async function save(): Promise<void> {
  const created = !id.value,
    savedId = await editor.save();
  if (!savedId) return;
  toast.success(created ? "Фид создан" : "Настройки сохранены");
  if (created)
    await router.replace({
      name: "feed-detail",
      params: { id: savedId },
      query: { returnTo: returnTo.value },
    });
}
function askArchive(): void {
  if (!editor.query.data.value || busy.value) return;
  archive.error.value = undefined;
  target.value = { ...editor.query.data.value };
}
async function confirmArchive(): Promise<void> {
  if (!target.value || archiveConflict.value) return;
  const result = await archive.execute({
    id: target.value.id,
    expectedVersion: target.value.version,
  });
  if (!result) return;
  target.value = null;
  editor.acknowledgeArchive();
  toast.success("Фид перемещён в архив");
  back();
}
</script>
<template>
  <Teleport to="#workspace-page-header" defer
    ><FeedHeader
      :title="
        id ? (editor.query.data.value?.name ?? 'Настройки фида') : 'Новый фид'
      "
      :archivable="!!editor.query.data.value && !editor.readonly.value"
      :busy="busy"
      @back="back"
      @archive="askArchive"
  /></Teleport>
  <div class="min-h-0 min-w-0 flex-1 overflow-y-auto">
    <div class="mx-auto flex w-full max-w-2xl flex-col gap-6 pb-8">
      <header class="flex flex-wrap items-center justify-between gap-3">
        <h1 class="text-2xl font-semibold">
          {{ id ? "Настройки фида" : "Новый фид" }}
        </h1>
        <FeedStatus
          v-if="editor.query.data.value && id"
          :status="editor.query.data.value.status"
        />
      </header>
      <FeedSections
        v-if="id"
        current="settings"
        :disabled="busy"
        @navigate="
          $event !== 'settings' &&
          router.push({
            name: feedSectionRoutes[$event],
            params: { id },
            query: { returnTo },
          })
        "
      />
      <Alert v-if="queryError" variant="destructive"
        ><AlertDescription
          class="flex flex-wrap items-center justify-between gap-3"
          >{{ queryError
          }}<Button
            variant="outline"
            :disabled="editor.query.isFetching.value"
            @click="editor.query.refetch()"
            >Повторить</Button
          ></AlertDescription
        ></Alert
      >
      <div
        v-if="id && !editor.draft.value && editor.query.isPending.value"
        role="status"
        aria-label="Загрузка настроек"
        class="flex flex-col gap-4"
      >
        <Skeleton v-for="row in 5" :key="row" class="h-12 w-full" />
      </div>
      <Alert v-if="editor.readonly.value"
        ><AlertDescription
          >Фид находится в архиве. Настройки доступны только для
          просмотра.</AlertDescription
        ></Alert
      >
      <Alert v-if="editor.error.value" variant="destructive"
        ><AlertDescription>{{ editor.error.value }}</AlertDescription></Alert
      >
      <Alert v-if="editor.conflict.value && !editor.readonly.value"
        ><AlertDescription class="flex flex-col items-start gap-3"
          >Серверная версия отличается от открытой. Ваш ввод сохранён. Загрузите
          актуальные настройки, чтобы продолжить редактирование.<Button
            variant="outline"
            :disabled="busy || editor.query.isFetching.value"
            @click="reset"
            >Загрузить актуальные настройки</Button
          ></AlertDescription
        ></Alert
      >
      <Button
        v-if="editor.uncertain.value"
        variant="outline"
        class="self-start"
        @click="back"
        >Проверить список фидов</Button
      >
      <FeedForm
        v-if="editor.draft.value"
        :key="editor.contextKey.value"
        :draft="editor.draft.value"
        :busy="busy"
        :dirty="editor.dirty.value"
        :creating="!id"
        :readonly="editor.readonly.value"
        :blocked="editor.conflict.value || editor.uncertain.value"
        :errors="editor.fields.value"
        @change="editor.draft.value = $event"
        @submit="save"
        @reset="reset"
      />
      <p v-if="!id" class="text-sm text-muted-foreground">
        Фид будет создан как черновик с пустой схемой.
      </p>
    </div>
    <ArchiveFeedDialog
      :open="!!target"
      :name="target?.name ?? ''"
      :code="target?.code ?? ''"
      :busy="archive.pending.value"
      :error="archiveError"
      :conflicted="archiveConflict"
      @update:open="!$event && (target = null)"
      @confirm="confirmArchive"
    />
  </div>
</template>
