<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Field, FieldLabel, FieldDescription } from "@/components/ui/field";
import ContentFeedForm from "../ui/feeds/ContentFeedForm.vue";
import FeedImportPanel from "../ui/feeds/FeedImportPanel.vue";
import { useChannelScope } from "../model/use-channel-scope";
import { useContentFeeds } from "../model/use-content-feeds";
import { useFeedImport } from "../model/use-feed-import";
import { useCreateContentFeed } from "../model/use-create-content-feed";
import { useSaveContentFeed } from "../model/use-save-content-feed";
import { usePreviewContentFeed } from "../model/use-preview-content-feed";
import { useEnableContentFeed } from "../model/use-enable-content-feed";
import { useDisableContentFeed } from "../model/use-disable-content-feed";
import { useRequestFeedImport } from "../model/use-request-feed-import";
import { useResumeFeedImport } from "../model/use-resume-feed-import";
import { useAttachFeedImport } from "../model/use-attach-feed-import";
import { useResolveFeedImport } from "../model/use-resolve-feed-import";
import {
  contentFeedError,
  contentFeedIssue,
} from "../model/content-feed.errors";
import type {
  FeedPreview,
  FeedImportRevisionInput,
} from "../model/content-feed.types";
const props = defineProps<{ channelId: string; verified: boolean }>();
const channelId = computed(() => props.channelId),
  scope = useChannelScope(),
  router = useRouter();
const contextKey = computed(() =>
  JSON.stringify([scope.value, props.channelId]),
);
const feeds = useContentFeeds(channelId),
  feed = computed(() => feeds.data.value?.[0] ?? null);
const feedId = computed(() => feed.value?.id ?? ""),
  operation = useFeedImport(channelId, feedId);
const create = useCreateContentFeed(),
  save = useSaveContentFeed(),
  preview = usePreviewContentFeed(),
  enable = useEnableContentFeed(),
  disable = useDisableContentFeed();
const request = useRequestFeedImport(),
  resume = useResumeFeedImport(),
  attach = useAttachFeedImport(),
  resolve = useResolveFeedImport();
const result = ref<FeedPreview | null>(null),
  previewRevision = ref<number | null>(null),
  error = ref(""),
  sourceDirty = ref(false),
  savedVersion = ref(0),
  pendingRequestId = ref<string | null>(null);
const busy = computed(() =>
  [
    create,
    save,
    preview,
    enable,
    disable,
    request,
    resume,
    attach,
    resolve,
  ].some((m) => m.isPending.value),
);
const ready = computed(
  () =>
    result.value?.ready === true &&
    previewRevision.value === feed.value?.revision &&
    !sourceDirty.value,
);
const locked = computed(
  () =>
    !!operation.data.value &&
    [
      "queued",
      "submitting",
      "processing",
      "verifying",
      "unknown",
      "needs_attention",
    ].includes(operation.data.value.phase),
);
const publicationLinks = computed(() =>
  Object.fromEntries(
    (operation.data.value?.verification ?? []).map((v) => [
      v.publicationId,
      router.resolve({
        name: "channel-publication",
        params: { id: props.channelId, publicationId: v.publicationId },
      }).href,
    ]),
  ),
);
watch(contextKey, () => {
  result.value = null;
  previewRevision.value = null;
  error.value = "";
  sourceDirty.value = false;
  savedVersion.value = 0;
  pendingRequestId.value = null;
});
watch(
  () => operation.data.value?.operationId,
  (id) => {
    if (id && id === pendingRequestId.value) pendingRequestId.value = null;
  },
);
async function perform(action: () => Promise<unknown>): Promise<void> {
  const captured = contextKey.value;
  error.value = "";
  try {
    await action();
  } catch (issue: unknown) {
    if (captured === contextKey.value) error.value = contentFeedError(issue);
  }
}
async function saveSource(
  sourceUrl: string,
  expectedRevision: number,
): Promise<void> {
  const captured = contextKey.value;
  error.value = "";
  try {
    if (feed.value)
      await save.mutateAsync({
        channelId: props.channelId,
        feedId: feed.value.id,
        sourceUrl,
        expectedRevision,
      });
    else await create.mutateAsync({ channelId: props.channelId, sourceUrl });
    if (captured === contextKey.value) {
      savedVersion.value++;
      result.value = null;
      previewRevision.value = null;
    }
  } catch (issue: unknown) {
    if (captured === contextKey.value) error.value = contentFeedError(issue);
  }
}
async function check(): Promise<void> {
  if (!feed.value) return;
  const captured = contextKey.value,
    revision = feed.value.revision;
  error.value = "";
  try {
    const value = await preview.mutateAsync({
      channelId: props.channelId,
      feedId: feed.value.id,
    });
    if (captured === contextKey.value) {
      result.value = value;
      previewRevision.value = revision;
    }
  } catch (issue: unknown) {
    if (captured === contextKey.value) {
      result.value = null;
      error.value = contentFeedError(issue);
    }
  }
}
function version(): FeedImportRevisionInput | null {
  return feed.value && operation.data.value
    ? {
        channelId: props.channelId,
        feedId: feed.value.id,
        expectedRevision: feed.value.revision,
        expectedDeliveryRevision: operation.data.value.revision,
      }
    : null;
}
async function start(forceUpdate: boolean): Promise<void> {
  const input = version();
  if (!input || !ready.value) return;
  pendingRequestId.value ??= crypto.randomUUID();
  await perform(() =>
    request.mutateAsync({
      ...input,
      requestId: pendingRequestId.value!,
      forceUpdate,
    }),
  );
}
async function continueImport(): Promise<void> {
  const input = version();
  if (input) await perform(() => resume.mutateAsync(input));
}
async function attachImport(externalId: string): Promise<void> {
  const input = version();
  if (input) await perform(() => attach.mutateAsync({ ...input, externalId }));
}
async function resolveImport(): Promise<void> {
  const input = version();
  if (input)
    await perform(() =>
      resolve.mutateAsync({ ...input, confirmNotSubmitted: true }),
    );
}
async function toggle(): Promise<void> {
  if (!feed.value) return;
  const captured = contextKey.value;
  const wasEnabled = feed.value.enabled;
  const checkedRevision = previewRevision.value;
  const input = {
    channelId: props.channelId,
    feedId: feed.value.id,
    expectedRevision: feed.value.revision,
  };
  await perform(async () => {
    const updated = wasEnabled
      ? await disable.mutateAsync(input)
      : await enable.mutateAsync(input);
    if (
      !wasEnabled &&
      captured === contextKey.value &&
      result.value?.ready &&
      checkedRevision === input.expectedRevision &&
      !sourceDirty.value
    )
      previewRevision.value = updated.revision;
  });
}
async function copy(): Promise<void> {
  if (!feed.value?.publicUrl) return;
  try {
    await navigator.clipboard.writeText(feed.value.publicUrl);
  } catch {
    error.value =
      "Не удалось скопировать ссылку. Её можно выделить в поле и скопировать вручную.";
  }
}
function refresh(): void {
  void feeds.refetch();
  void operation.refetch();
}
</script>
<template>
  <div
    class="flex min-w-0 flex-col gap-5 overflow-y-auto pb-6"
    aria-label="XML-фид Prom"
  >
    <Skeleton v-if="feeds.isPending.value" class="h-64 w-full" />
    <Alert v-if="feeds.error.value" variant="destructive"
      ><AlertDescription class="flex flex-wrap items-center gap-2"
        >{{ contentFeedError(feeds.error.value)
        }}<Button variant="outline" @click="feeds.refetch()"
          >Повторить чтение</Button
        ></AlertDescription
      ></Alert
    >
    <Alert v-if="error" variant="destructive"
      ><AlertDescription>{{ error }}</AlertDescription></Alert
    >
    <template v-if="!feeds.isPending.value && (!feeds.error.value || feed)">
      <Card
        ><CardHeader
          ><CardTitle>XML-фид Prom</CardTitle
          ><CardDescription
            >Постоянная ссылка на полный каталог с контентом разрешённых
            представлений.</CardDescription
          ></CardHeader
        ><CardContent class="flex min-w-0 flex-col gap-5">
          <ContentFeedForm
            :key="contextKey + feedId"
            :feed="feed"
            :busy="busy"
            :locked="locked"
            :saved-version="savedVersion"
            @save="saveSource"
            @dirty="sourceDirty = $event"
          />
          <template v-if="feed">
            <Field
              ><FieldLabel for="feed-public-url">Постоянная ссылка</FieldLabel>
              <div class="flex min-w-0 flex-col gap-2 sm:flex-row">
                <Input
                  id="feed-public-url"
                  :model-value="
                    feed.publicUrl ?? 'Публичный HTTPS-адрес пока не настроен'
                  "
                  readonly
                  class="min-w-0 flex-1"
                /><Button
                  type="button"
                  variant="outline"
                  :disabled="!feed.publicUrl"
                  @click="copy"
                  >Скопировать</Button
                >
              </div>
              <FieldDescription
                >Ссылка открывает XML без Console-сессии. Храните её как данные
                доступа.</FieldDescription
              ></Field
            >
            <div class="flex flex-wrap items-center gap-3">
              <Button
                variant="outline"
                :disabled="busy || sourceDirty"
                @click="check"
                >Проверить preview</Button
              ><Button
                variant="outline"
                :disabled="busy || (!feed.enabled && !ready)"
                @click="toggle"
                >{{
                  feed.enabled
                    ? "Выключить выдачу фида"
                    : "Включить выдачу фида"
                }}</Button
              ><span class="text-sm text-muted-foreground">{{
                feed.enabled ? "Фид включён" : "Фид выключен"
              }}</span>
            </div>
            <Alert v-if="ready"
              ><AlertDescription
                >Фид сформирован: {{ result?.statistics?.offers }} позиций,
                изменено {{ result?.statistics?.changedOffers }}. Проверка
                относится к сохранённому источнику.</AlertDescription
              ></Alert
            >
            <Alert v-else-if="result && !result.ready" variant="destructive"
              ><AlertDescription
                ><ul class="flex flex-col gap-1">
                  <li v-for="(issue, index) in result.issues" :key="index">
                    {{ contentFeedIssue(issue.code) }}
                  </li>
                </ul></AlertDescription
              ></Alert
            >
            <p
              v-if="
                previewRevision !== null && previewRevision !== feed.revision
              "
              class="text-sm text-muted-foreground"
            >
              Настройки изменились. Проверьте актуальный фид.
            </p>
          </template>
        </CardContent></Card
      >
      <template v-if="feed">
        <Skeleton v-if="operation.isPending.value" class="h-48 w-full" />
        <Alert v-if="operation.error.value" variant="destructive"
          ><AlertDescription class="flex flex-wrap items-center gap-2"
            >{{ contentFeedError(operation.error.value)
            }}<Button variant="outline" @click="operation.refetch()"
              >Повторить чтение</Button
            ></AlertDescription
          ></Alert
        >
        <FeedImportPanel
          :operation="operation.data.value ?? null"
          :busy="busy"
          :ready="ready"
          :enabled="feed.enabled"
          :verified="verified"
          :publication-links="publicationLinks"
          @start="start"
          @resume="continueImport"
          @attach="attachImport"
          @resolve="resolveImport"
          @refresh="refresh"
        />
      </template>
    </template>
  </div>
</template>
