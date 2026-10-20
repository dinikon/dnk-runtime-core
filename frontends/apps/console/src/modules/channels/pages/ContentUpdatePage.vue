<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { catalogItemLocation } from "@/modules/catalog";
import { useChannelsContext } from "../model/use-channels-context";
import { useContentUpdateQuery } from "../model/queries/use-content-update-query";
import { useChannelQuery } from "../model/queries/use-channel-query";
import { useStartContentUpdate } from "../model/mutations/use-start-content-update";
import { useConfirmContentUpdate } from "../model/mutations/use-confirm-content-update";
import { useRetryContentUpdate } from "../model/mutations/use-retry-content-update";
import { useSetOutbound } from "../model/mutations/use-set-outbound";
import { channelErrorMessage } from "../model/channels.errors";
import {
  contentUpdateLabel,
  contentUpdateActive,
  canConfirmContentUpdate,
} from "../model/content-update.presentation";
import { reasonLabel } from "../model/channels.presentation";
import ContentUpdateComparison from "../ui/ContentUpdateComparison.vue";
import ChannelsQueryBody from "../ui/ChannelsQueryBody.vue";
const route = useRoute(),
  router = useRouter(),
  ctx = useChannelsContext();
const id = computed(() => String(route.params.runId ?? ""));
const channelId = computed(() => String(route.params.channelId ?? ""));
const initialized = ref(false),
  actionError = ref<string | null>(null);
const start = useStartContentUpdate(ctx),
  confirm = useConfirmContentUpdate(ctx),
  retry = useRetryContentUpdate(ctx),
  outbound = useSetOutbound(ctx);
const query = useContentUpdateQuery(ctx, id, initialized),
  channel = useChannelQuery(ctx, channelId);
const run = computed(() =>
  query.data.value?.id === id.value &&
  query.data.value.channelId === channelId.value
    ? query.data.value
    : undefined,
);
const locales = computed(
  () => run.value?.items[0]?.desired.map((text) => text.locale) ?? [],
);
const locale = computed(() =>
  typeof route.query.locale === "string" &&
  locales.value.includes(route.query.locale)
    ? route.query.locale
    : (locales.value[0] ?? ""),
);
const busy = computed(
  () =>
    start.isPending.value ||
    confirm.isPending.value ||
    retry.isPending.value ||
    outbound.isPending.value,
);
const completed = computed(
  () =>
    run.value?.items.filter(
      (item) =>
        ![
          "preview_pending",
          "pending",
          "sending",
          "verifying",
          "reconciling",
        ].includes(item.status),
    ).length ?? 0,
);
const readyCount = computed(
  () => run.value?.items.filter((item) => item.status === "ready").length ?? 0,
);
const active = computed(() => contentUpdateActive(run.value));
const canConfirm = computed(
  () => !!run.value && canConfirmContentUpdate(run.value),
);
const canVerify = computed(
  () =>
    run.value?.confirmedAt &&
    ["failed", "partial"].includes(run.value.status) &&
    run.value.items.some((item) => ["failed", "unknown"].includes(item.status)),
);
let initSequence = 0;
async function initialize(): Promise<void> {
  const sequence = ++initSequence,
    current = ctx.capture();
  initialized.value = false;
  actionError.value = null;
  const selected =
    typeof route.query.publications === "string"
      ? route.query.publications.split(",").filter(Boolean)
      : [];
  if (!selected.length) {
    initialized.value = true;
    return;
  }
  try {
    await start.mutateAsync({
      runId: id.value,
      channelId: channelId.value,
      publicationIds: selected,
    });
    if (current() && sequence === initSequence) initialized.value = true;
  } catch (error: unknown) {
    if (current() && sequence === initSequence)
      actionError.value = channelErrorMessage(error);
  }
}
watch(
  () => [ctx.scope.value, ctx.enabled.value, id.value],
  () => {
    if (ctx.enabled.value) void initialize();
  },
  { immediate: true },
);
async function send(): Promise<void> {
  if (!run.value?.previewHash || busy.value) return;
  const current = ctx.capture();
  actionError.value = null;
  const input = {
    runId: run.value.id,
    revision: run.value.revision,
    previewHash: run.value.previewHash,
  };
  try {
    await confirm.mutateAsync(input);
  } catch (error: unknown) {
    if (current()) actionError.value = channelErrorMessage(error);
  }
}
async function verify(): Promise<void> {
  if (!run.value || busy.value) return;
  const current = ctx.capture();
  actionError.value = null;
  try {
    await retry.mutateAsync({
      runId: run.value.id,
      revision: run.value.revision,
    });
  } catch (error: unknown) {
    if (current()) actionError.value = channelErrorMessage(error);
  }
}
async function setOutbound(enabled: boolean): Promise<void> {
  if (!channel.data.value || busy.value) return;
  const current = ctx.capture();
  actionError.value = null;
  try {
    await outbound.mutateAsync({
      channelId: channelId.value,
      revision: channel.data.value.revision,
      enabled,
    });
  } catch (error: unknown) {
    if (current()) actionError.value = channelErrorMessage(error);
  }
}
function prepareAgain(): void {
  if (!run.value || busy.value) return;
  void router.push({
    name: "channel-content-update",
    params: { channelId: channelId.value, runId: crypto.randomUUID() },
    query: {
      publications: run.value.items.map((item) => item.publicationId).join(","),
    },
  });
}
function openCatalog(itemId: string, selectedLocale: string): void {
  void router.push(catalogItemLocation(itemId, selectedLocale));
}
function setLocale(value: string): void {
  void router.replace({ query: { ...route.query, locale: value } });
}
</script>
<template>
  <div class="flex min-w-0 flex-col gap-5 p-4 md:p-6">
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div class="flex min-w-0 items-start gap-3">
        <Button
          variant="ghost"
          size="icon"
          aria-label="Назад к каналу"
          @click="
            router.push({ name: 'channel-detail', params: { channelId } })
          "
          ><ArrowLeft
        /></Button>
        <div>
          <h1 class="text-xl font-semibold">Обновление текстов публикаций</h1>
          <p class="text-muted-foreground text-sm">
            Названия и описания из каталога · {{ channel.data.value?.name }}
          </p>
        </div>
      </div>
      <Badge v-if="run" variant="outline">{{ contentUpdateLabel(run) }}</Badge>
    </header>
    <Alert v-if="actionError" variant="destructive"
      ><AlertDescription
        >{{ actionError }}
        <Button
          v-if="!initialized"
          variant="outline"
          size="sm"
          :disabled="busy"
          @click="initialize"
          >Повторить подготовку</Button
        ></AlertDescription
      ></Alert
    >
    <ChannelsQueryBody
      :pending="start.isPending.value || (initialized && query.isPending.value)"
      :error="query.error.value ? channelErrorMessage(query.error.value) : null"
      :has-data="!!run"
      :empty="false"
      empty-title=""
      empty-description=""
      @retry="query.refetch()"
    >
      <template v-if="run">
        <Alert v-if="!run.outboundEnabled && !run.confirmedAt && readyCount"
          ><AlertTitle>Исходящие операции выключены</AlertTitle>
          <AlertDescription
            >Сравнение доступно. Разрешение обновлений само по себе не
            отправляет данные.
            <Button
              v-if="readyCount"
              class="mt-3"
              variant="outline"
              :disabled="busy || !channel.data.value"
              @click="setOutbound(true)"
              >Разрешить ручные обновления</Button
            ></AlertDescription
          ></Alert
        >
        <Alert v-if="run.status === 'blocked'">
          <AlertTitle>Отправка недоступна</AlertTitle>
          <AlertDescription>{{
            reasonLabel(
              run.items.find((item) => item.issues.length)?.issues[0] ??
                "content_update_write_unsupported",
            )
          }}</AlertDescription>
        </Alert>
        <Alert v-if="run.interrupted"
          ><AlertTitle>Выполнение прервано</AlertTitle
          ><AlertDescription
            >Продолжим с сохранённого шага. Отправку с неизвестным результатом
            сначала проверим.
            <Button
              class="mt-3"
              variant="outline"
              :disabled="busy"
              @click="verify"
              >Продолжить</Button
            ></AlertDescription
          ></Alert
        >
        <Card
          ><CardContent class="flex flex-col gap-3 pt-6">
            <p v-if="run.status === 'blocked'" class="text-sm">
              Сравнение сохранено. Отправка недоступна для выбранных публикаций.
            </p>
            <p
              v-else-if="
                !run.confirmedAt && run.status === 'ready' && !readyCount
              "
              class="text-sm"
            >
              Названия и описания уже совпадают с каталогом. Отправка не
              требуется.
            </p>
            <p v-else-if="!run.confirmedAt" class="text-sm">
              Готово к обновлению: {{ readyCount }} из {{ run.items.length }}.
              Проверьте тексты перед отправкой.
            </p>
            <p v-else class="text-sm">
              Проверено позиций: {{ completed }} из {{ run.items.length }}.
              Успех подтверждается чтением площадки.
            </p>
            <Progress
              v-if="active"
              :model-value="(100 * completed) / Math.max(1, run.items.length)"
              aria-label="Прогресс обновления текстов"
            />
            <div class="flex flex-wrap gap-2">
              <Button
                v-if="!run.confirmedAt"
                :disabled="busy || !canConfirm"
                @click="send"
                >{{
                  confirm.isPending.value
                    ? "Принимаем обновление…"
                    : "Обновить публикации"
                }}</Button
              >
              <Button
                v-if="canVerify"
                variant="outline"
                :disabled="busy"
                @click="verify"
                >Проверить результат ещё раз</Button
              >
              <Button
                v-if="!active"
                variant="outline"
                :disabled="busy"
                @click="prepareAgain"
                >Пересобрать сравнение</Button
              >
              <Button
                v-if="run.outboundEnabled && !run.confirmedAt"
                variant="ghost"
                :disabled="busy"
                @click="setOutbound(false)"
                >Выключить исходящие операции</Button
              >
            </div>
            <p class="text-muted-foreground text-xs">
              Тексты редактируются в каталоге. После исправления пересоберите
              сравнение.
            </p>
          </CardContent></Card
        >
        <Tabs
          v-if="locales.length"
          :model-value="locale"
          @update:model-value="(value) => setLocale(String(value))"
          ><TabsList
            ><TabsTrigger v-for="code in locales" :key="code" :value="code">{{
              code.toUpperCase()
            }}</TabsTrigger></TabsList
          ></Tabs
        >
        <ContentUpdateComparison
          v-for="item in run.items"
          :key="item.publicationId"
          :item="item"
          :confirmed="!!run.confirmedAt"
          :locale="locale"
          @open-catalog="openCatalog"
        />
      </template>
    </ChannelsQueryBody>
  </div>
</template>
