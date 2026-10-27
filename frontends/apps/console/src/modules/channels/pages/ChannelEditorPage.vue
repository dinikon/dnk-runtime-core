<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import ChannelForm from "../ui/ChannelForm.vue";
import ChannelStatus from "../ui/ChannelStatus.vue";
import DeleteChannelDialog from "../ui/DeleteChannelDialog.vue";
import { useChannel, useChannelPlatforms } from "../model/channel.queries";
import { useSaveChannel } from "../model/use-save-channel";
import { useVerifyChannel } from "../model/use-verify-channel";
import { useDeleteChannel } from "../model/use-delete-channel";
import { useChannelScope } from "../model/use-channel-scope";
import { draftFor, saveDraft, shouldPoll } from "../model/channel.schema";
import { channelErrorMessage } from "../model/channel.errors";
import type { ChannelDraft } from "../model/channel.types";
const route = useRoute(),
  router = useRouter(),
  scope = useChannelScope();
const id = computed(() => String(route.params.id ?? ""));
const query = useChannel(id),
  platforms = useChannelPlatforms(),
  saveAction = useSaveChannel(),
  verifyAction = useVerifyChannel(),
  deleteAction = useDeleteChannel();
const draft = ref<ChannelDraft | null>(null),
  baseRevision = ref(0),
  deleteOpen = ref(false);
let loadedKey = "",
  baseline = "",
  baselineConfigRevision = 0;
const contextKey = computed(() => JSON.stringify(scope.value) + ":" + id.value);
watch(
  contextKey,
  () => {
    loadedKey = "";
    draft.value = null;
    deleteOpen.value = false;
  },
  { flush: "sync" },
);
function fingerprint(value: ChannelDraft): string {
  return JSON.stringify([
    value.name,
    value.platformKind,
    value.endpoint,
    value.settings,
  ]);
}
function resetDraft(): void {
  const channel = id.value ? query.data.value : undefined;
  if (id.value && !channel) return;
  const platform =
    platforms.data.value?.find((p) => p.kind === channel?.platformKind) ??
    platforms.data.value?.[0];
  if (!platform) return;
  draft.value = draftFor(platform, channel);
  baseRevision.value = channel?.revision ?? 0;
  baselineConfigRevision = channel?.configRevision ?? 0;
  baseline = fingerprint(draft.value);
  loadedKey = contextKey.value;
}
watch(
  [platforms.data, query.data, contextKey],
  () => {
    if (loadedKey !== contextKey.value) resetDraft();
    else {
      const channel = query.data.value;
      const installed = platforms.data.value?.find(
        (p) => p.kind === channel?.platformKind,
      );
      if (
        channel &&
        installed &&
        channel.configRevision === baselineConfigRevision &&
        fingerprint(draftFor(installed, channel)) === baseline
      ) {
        baseRevision.value = channel.revision;
      }
    }
  },
  { immediate: true },
);
const platform = computed(() =>
  platforms.data.value?.find((p) => p.kind === draft.value?.platformKind),
);
const busy = computed(
  () =>
    saveAction.pending.value ||
    verifyAction.pending.value ||
    deleteAction.pending.value,
);
const dirty = computed(
  () =>
    !!draft.value &&
    (draft.value.replaceCredentials || fingerprint(draft.value) !== baseline),
);
const error = computed(
  () => saveAction.error.value || verifyAction.error.value,
);
function changePlatform(kind: string): void {
  const next = platforms.data.value?.find((p) => p.kind === kind);
  if (!next || id.value || !draft.value) return;
  draft.value = { ...draftFor(next), name: draft.value.name };
}
async function save(): Promise<void> {
  if (!draft.value || !platform.value) return;
  const captured = contextKey.value;
  const result = await saveAction.execute({
    id: id.value || undefined,
    revision: baseRevision.value,
    value: saveDraft(draft.value, platform.value),
  });
  if (result && contextKey.value === captured) {
    if (!id.value) {
      await router.push("/channels/" + result.value.id);
    } else {
      resetDraft();
    }
  }
}
async function verify(): Promise<void> {
  if (!id.value || dirty.value) return;
  await verifyAction.execute(id.value);
}
async function remove(): Promise<void> {
  if (!query.data.value) return;
  const captured = contextKey.value;
  const result = await deleteAction.execute({
    id: id.value,
    revision: query.data.value.revision,
  });
  if (result && contextKey.value === captured) await router.push("/channels");
}
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-auto pb-6">
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <Button variant="link" class="px-0" @click="router.push('/channels')"
          >Все каналы</Button
        >
        <h1 class="text-2xl font-semibold">
          {{ id ? (query.data.value?.name ?? "Канал") : "Подключить магазин" }}
        </h1>
      </div>
      <Button
        v-if="id && query.data.value"
        variant="outline"
        :disabled="busy"
        @click="deleteOpen = true"
        >Удалить канал</Button
      >
    </header>
    <Skeleton
      v-if="platforms.isPending.value || (id && query.isPending.value)"
      class="h-64 w-full"
    /><Alert
      v-else-if="platforms.error.value || (id && query.error.value)"
      variant="destructive"
      ><AlertDescription class="flex flex-wrap items-center gap-3"
        >{{ channelErrorMessage(platforms.error.value ?? query.error.value)
        }}<Button
          variant="outline"
          @click="
            platforms.refetch();
            query.refetch();
          "
          >Повторить</Button
        ></AlertDescription
      ></Alert
    ><template v-else-if="draft && platform"
      ><Card v-if="query.data.value"
        ><CardHeader
          ><CardTitle><ChannelStatus :channel="query.data.value" /></CardTitle
          ><CardDescription>{{
            query.data.value.identity
              ? "Магазин: " + query.data.value.identity.key
              : "Identity магазина ещё не подтверждена."
          }}</CardDescription></CardHeader
        ><CardContent class="flex flex-col items-start gap-3"
          ><p
            v-if="query.data.value.recoveryRequired"
            role="status"
            class="text-sm"
          >
            Задание проверки прервано. Запустите проверку снова.
          </p>
          <p
            v-else-if="query.data.value.verification.errorCode"
            role="status"
            class="text-sm"
          >
            {{ channelErrorMessage(query.data.value.verification.errorCode) }}
          </p>
          <Button
            variant="outline"
            :disabled="
              busy ||
              dirty ||
              shouldPoll(query.data.value) ||
              !query.data.value.availableCapabilities.includes(
                'verify_connection',
              )
            "
            @click="verify"
            >Проверить подключение</Button
          >
          <p v-if="dirty" class="text-sm text-muted-foreground">
            Сначала сохраните изменения формы.
          </p></CardContent
        ></Card
      ><Alert v-if="error" variant="destructive"
        ><AlertDescription>{{ error }}</AlertDescription></Alert
      ><Alert
        v-if="
          id && query.data.value && baseRevision !== query.data.value.revision
        "
        ><AlertDescription class="flex flex-col items-start gap-3"
          >Сохранённый канал изменился. Черновик оставлен без изменений.
          <div class="flex flex-wrap gap-2">
            <Button variant="outline" :disabled="busy" @click="resetDraft"
              >Загрузить актуальные настройки</Button
            ><Button
              variant="outline"
              :disabled="busy"
              @click="baseRevision = query.data.value.revision"
              >Применить черновик к актуальной версии</Button
            >
          </div></AlertDescription
        ></Alert
      ><Card
        ><CardHeader
          ><CardTitle>Настройки подключения</CardTitle
          ><CardDescription>{{ platform.title }}</CardDescription></CardHeader
        ><CardContent
          ><ChannelForm
            :draft="draft"
            :platform="platform"
            :platforms="platforms.data.value ?? []"
            :editing="!!id"
            :busy="busy"
            @change="draft = $event"
            @platform="changePlatform"
            @submit="save" /></CardContent></Card></template
    ><DeleteChannelDialog
      v-if="query.data.value"
      v-model:open="deleteOpen"
      :name="query.data.value.name"
      :busy="deleteAction.pending.value"
      :error="deleteAction.error.value"
      @confirm="remove"
    />
  </div>
</template>
