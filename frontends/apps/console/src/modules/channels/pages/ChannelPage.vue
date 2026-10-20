<script setup lang="ts">
import PublicationIdentitySummary from "../ui/PublicationIdentitySummary.vue";
import { computed, ref, watch, watchEffect, onBeforeUnmount } from "vue";
import {
  useRoute,
  useRouter,
  onBeforeRouteLeave,
  onBeforeRouteUpdate,
} from "vue-router";
import { ArrowLeft } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useChannelsContext } from "../model/use-channels-context";
import { useChannelsPageState } from "../model/use-channels-page-state";
import { useChannelQuery } from "../model/queries/use-channel-query";
import { usePlatformQuery } from "../model/queries/use-platform-query";
import { useConnectionReferencesQuery } from "../model/queries/use-references-query";
import { useConnectionQuery } from "../model/queries/use-connection-query";
import { useInitializationQuery } from "../model/queries/use-initialization-query";
import { usePublicationsQuery } from "../model/queries/use-publications-query";
import { useCreateConnection } from "../model/mutations/use-create-connection";
import { useUpdateConnection } from "../model/mutations/use-update-connection";
import { useVerifyConnection } from "../model/mutations/use-verify-connection";
import { usePauseConnection } from "../model/mutations/use-pause-connection";
import { useResumeConnection } from "../model/mutations/use-resume-connection";
import { useStartInitialization } from "../model/mutations/use-start-initialization";
import { channelErrorMessage } from "../model/channels.errors";
import { ChannelsApiError } from "../api/channels.error";
import {
  connectionActive,
  initializationActive,
  platformSupported,
  reasonLabel,
} from "../model/channels.presentation";
import type { ConnectionSettings } from "../model/channels.types";
import ChannelStatusBadge from "../ui/ChannelStatusBadge.vue";
import ChannelsQueryBody from "../ui/ChannelsQueryBody.vue";
import ChannelsPagination from "../ui/ChannelsPagination.vue";
import ChannelInitializationCard from "../ui/ChannelInitializationCard.vue";
import ConnectionForm from "../ui/ConnectionForm.vue";
import PublicationsToolbar from "../ui/PublicationsToolbar.vue";
import PublicationsList from "../ui/PublicationsList.vue";
import ContentUpdatesHistory from "../ui/ContentUpdatesHistory.vue";
import { useContentUpdatesQuery } from "../model/queries/use-content-updates-query";

import { toast } from "vue-sonner";
import { catalogItemLocation } from "@/modules/catalog";
import type { Publication } from "../model/channels.types";
import type { CatalogCandidate } from "../model/catalog-links.types";
import { useCatalogCandidateState } from "../model/use-catalog-candidate-state";
import { useCatalogCandidatesQuery } from "../model/queries/use-catalog-candidates-query";
import { useBindPublication } from "../model/mutations/use-bind-publication";
import { useUnbindPublication } from "../model/mutations/use-unbind-publication";
import BindPublicationDialog from "../ui/BindPublicationDialog.vue";
import UnbindPublicationDialog from "../ui/UnbindPublicationDialog.vue";

const context = useChannelsContext(),
  state = useChannelsPageState(),
  route = useRoute(),
  router = useRouter();
const id = computed(() => String(route.params.channelId ?? ""));
const channel = useChannelQuery(context, id);
const history = useContentUpdatesQuery(context, id);
const contentSelection = ref<string[]>([]);
function selectContent(id: string, selected: boolean): void {
  contentSelection.value = selected
    ? [...new Set([...contentSelection.value, id])]
    : contentSelection.value.filter((value) => value !== id);
}
function openContentUpdate(publicationIds: string[]): void {
  if (!publicationIds.length) return;
  void router.push({
    name: "channel-content-update",
    params: { channelId: id.value, runId: crypto.randomUUID() },
    query: { publications: publicationIds.join(",") },
  });
}
function openContentResult(runId: string): void {
  void router.push({
    name: "channel-content-update",
    params: { channelId: id.value, runId },
  });
}
watch(
  [
    () => context.scope.value,
    id,
    () => route.query.page,
    () => route.query.search,
    () => route.query.binding,
    () => route.query.stock,
    () => route.query.identity,
    () => route.query.identityKey,
  ],
  () => {
    contentSelection.value = [];
  },
);
const platform = usePlatformQuery(
  context,
  () => channel.data.value?.platformKind ?? "",
);
watch(
  () => platform.data.value,
  (value) => {
    if (
      value &&
      !value.capabilities.includes("publication_identity_diagnostics") &&
      (state.identityStatus.value || state.identityKey.value)
    )
      state.setFilters({
        search: state.search.value,
        stockStatus: state.stockStatus.value,
        bindingStatus: state.bindingStatus.value,
        identityStatus: "",
      });
  },
);
const references = useConnectionReferencesQuery(context);
const connectionPolling = ref(false),
  initializationPolling = ref(false);
const connection = useConnectionQuery(
  context,
  id,
  () => !!channel.data.value?.connectionId,
  connectionPolling,
);
const connectionId = computed(() => channel.data.value?.connectionId ?? "");
const initialization = useInitializationQuery(
  context,
  connectionId,
  initializationPolling,
);
const publications = usePublicationsQuery(
  context,
  connectionId,
  state.publicationFilters,
  () => initializationPolling.value,
);
const createConnection = useCreateConnection(context),
  updateConnection = useUpdateConnection(context),
  verify = useVerifyConnection(context),
  pause = usePauseConnection(context),
  resume = useResumeConnection(context),
  start = useStartInitialization(context);
const actionError = ref<string | null>(null),
  saveSequence = ref(0),
  dirty = ref(false);
const initializationRequest = ref<string | null>(null);
const pending = computed(
  () =>
    createConnection.isPending.value ||
    updateConnection.isPending.value ||
    verify.isPending.value ||
    pause.isPending.value ||
    resume.isPending.value ||
    start.isPending.value,
);
const revision = computed(() =>
  Math.max(
    channel.data.value?.revision ?? 1,
    connection.data.value?.revision ?? 1,
  ),
);
const active = computed(() =>
  connectionActive(
    connection.data.value,
    channel.data.value?.isArchived ?? false,
  ),
);
watchEffect(() => {
  const connected = connection.data.value;
  const canPoll =
    active.value && !connection.error.value && !initialization.error.value;
  const verifying = connected?.verificationStatus === "queued";
  const importing = initializationActive(initialization.data.value);
  const awaitingRun =
    connected?.verificationStatus === "verified" &&
    initialization.data.value?.status === "not_started";
  connectionPolling.value = canPoll && (verifying || importing || awaitingRun);
  initializationPolling.value =
    canPoll && (verifying || importing || awaitingRun);
});
watch(
  () => [
    initialization.data.value?.status,
    initialization.data.value?.readComplete,
    initialization.data.value?.recoveryRequired,
  ],
  (_next, previous) => {
    if (
      previous &&
      (previous[0] === "running" || previous[0] === "queued") &&
      !initializationActive(initialization.data.value)
    ) {
      void publications.refetch();
      void connection.refetch();
      void channel.refetch();
    }
  },
);
watch(
  () => connection.data.value?.generation,
  () => (initializationRequest.value = null),
);

const catalogAction = ref<"bind" | "unbind" | null>(null),
  selectedPublication = ref<Publication | null>(null),
  catalogActionError = ref<string | null>(null);
const selectedId = computed(() => selectedPublication.value?.id ?? "");
const candidateState = useCatalogCandidateState(selectedId);
const candidates = useCatalogCandidatesQuery(
  context,
  candidateState.filters,
  () => catalogAction.value === "bind" && !!selectedId.value,
);
const bindPublication = useBindPublication(context),
  unbindPublication = useUnbindPublication(context);
const catalogBusy = computed(
  () => bindPublication.isPending.value || unbindPublication.isPending.value,
);
function sourceLocale(publication: Publication): string {
  return publication.titleLocale ?? "";
}
function openCatalogAction(
  action: "bind" | "draft" | "unbind",
  publication: Publication,
): void {
  if (catalogBusy.value) return;
  if (action === "draft") {
    void router.push({
      name: "channel-publication-import",
      params: {
        channelId: id.value,
        publicationId: publication.id,
        preparationId: crypto.randomUUID(),
      },
      query: { revision: String(publication.observedRevision) },
    });
    return;
  }
  selectedPublication.value = publication;
  catalogAction.value = action;
  catalogActionError.value = null;
  candidateState.reset(sourceLocale(publication));
}
function closeCatalogAction(): void {
  if (catalogBusy.value) return;
  catalogAction.value = null;
  selectedPublication.value = null;
  catalogActionError.value = null;
}
function openCatalogItem(publication: Publication): void {
  if (publication.catalogItemId)
    void router.push(
      catalogItemLocation(publication.catalogItemId, sourceLocale(publication)),
    );
}
async function bindSelected(candidate: CatalogCandidate): Promise<void> {
  const publication = selectedPublication.value;
  if (!publication || catalogBusy.value) return;
  const current = context.capture();
  catalogActionError.value = null;
  try {
    await bindPublication.mutateAsync({
      publicationId: publication.id,
      catalogItemId: candidate.id,
      expectedRevision: candidate.representationRevision,
    });
    if (current()) {
      closeCatalogAction();
      toast.success("Публикация связана с товаром");
    }
  } catch (error: unknown) {
    if (current()) catalogActionError.value = channelErrorMessage(error);
  } finally {
    bindPublication.reset();
  }
}
async function unbindSelected(): Promise<void> {
  const publication = selectedPublication.value;
  if (
    !publication?.bindingId ||
    publication.representationRevision === null ||
    catalogBusy.value
  )
    return;
  const current = context.capture();
  catalogActionError.value = null;
  try {
    await unbindPublication.mutateAsync({
      publicationId: publication.id,
      bindingId: publication.bindingId,
      expectedRevision: publication.representationRevision,
    });
    if (current()) {
      closeCatalogAction();
      toast.success("Связь снята. Товар сохранён");
    }
  } catch (error: unknown) {
    if (current()) catalogActionError.value = channelErrorMessage(error);
  } finally {
    unbindPublication.reset();
  }
}
function canLeave(): boolean {
  return (
    !pending.value &&
    !catalogBusy.value &&
    (!dirty.value ||
      window.confirm(
        "Есть несохранённые настройки подключения. Отказаться от них?",
      ))
  );
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate((to, from) =>
  to.params.channelId === from.params.channelId &&
  to.query.tab === from.query.tab
    ? true
    : canLeave(),
);
function beforeUnload(event: BeforeUnloadEvent): void {
  if (dirty.value || pending.value) {
    event.preventDefault();
    event.returnValue = "";
  }
}
window.addEventListener("beforeunload", beforeUnload);
onBeforeUnmount(() => window.removeEventListener("beforeunload", beforeUnload));
function changeTab(value: string): void {
  if (canLeave()) {
    dirty.value = false;
    state.setTab(value);
  }
}
async function save(input: {
  revision: number;
  settings: ConnectionSettings;
  credentials?: Record<string, string>;
}): Promise<void> {
  if (pending.value) return;
  const current = context.capture();
  actionError.value = null;
  try {
    if (connectionId.value)
      await updateConnection.execute({ ...input, channelId: id.value });
    else
      await createConnection.execute({
        ...input,
        channelId: id.value,
        credentials: input.credentials ?? {},
      });
    if (current()) {
      saveSequence.value++;
      dirty.value = false;
    }
  } catch (error: unknown) {
    if (current()) actionError.value = channelErrorMessage(error);
  } finally {
    createConnection.reset();
    updateConnection.reset();
  }
}
async function connectionAction(
  action: "verify" | "pause" | "resume",
): Promise<void> {
  if (pending.value || dirty.value) return;
  const mutation =
    action === "verify" ? verify : action === "pause" ? pause : resume;
  const current = context.capture();
  actionError.value = null;
  try {
    await mutation.mutateAsync({
      channelId: id.value,
      revision: revision.value,
    });
  } catch (error: unknown) {
    if (current()) actionError.value = channelErrorMessage(error);
  } finally {
    mutation.reset();
  }
}
async function startInitialization(): Promise<void> {
  if (pending.value || !connectionId.value) return;
  const current = context.capture();
  actionError.value = null;
  initializationRequest.value ??= crypto.randomUUID();
  try {
    await start.mutateAsync({
      connectionId: connectionId.value,
      requestKey: initializationRequest.value,
    });
    if (current()) initializationRequest.value = null;
  } catch (error: unknown) {
    if (current()) {
      actionError.value = channelErrorMessage(error);
      if (
        error instanceof ChannelsApiError &&
        error.status &&
        error.status >= 400 &&
        error.status < 500
      )
        initializationRequest.value = null;
    }
  } finally {
    start.reset();
  }
}
</script>
<template>
  <main class="flex min-h-0 flex-1 flex-col gap-5 overflow-auto">
    <div>
      <Button
        variant="ghost"
        size="sm"
        @click="router.push({ name: 'channels-list' })"
        ><ArrowLeft data-icon="inline-start" />Все каналы</Button
      >
    </div>
    <ChannelsQueryBody
      :pending="channel.isPending.value"
      :error="
        channel.error.value ? channelErrorMessage(channel.error.value) : null
      "
      :has-data="!!channel.data.value"
      :empty="false"
      empty-title="Канал не найден"
      empty-description=""
      @retry="channel.refetch()"
      ><template v-if="channel.data.value"
        ><header class="flex flex-wrap items-start justify-between gap-4">
          <div class="flex min-w-0 flex-col gap-2">
            <div class="flex flex-wrap items-center gap-3">
              <h1 class="break-words text-2xl font-semibold tracking-tight">
                {{ channel.data.value.name }}
              </h1>
              <ChannelStatusBadge
                :status="
                  connection.data.value?.verificationStatus ??
                  channel.data.value.verificationStatus
                "
                :paused="
                  connection.data.value?.isPaused ?? channel.data.value.isPaused
                "
                :archived="channel.data.value.isArchived"
              />
            </div>
            <p class="text-muted-foreground text-sm">
              {{
                platform.data.value?.label ?? channel.data.value.platformKind
              }}
            </p>
          </div>
          <Badge variant="outline">{{
            channel.data.value.isEnabled
              ? "Исходящие операции разрешены"
              : "Исходящая синхронизация выключена"
          }}</Badge>
        </header>
        <Alert v-if="channel.data.value.isArchived"
          ><AlertTitle>Канал архивирован</AlertTitle
          ><AlertDescription
            >Сохранённые публикации доступны для просмотра.</AlertDescription
          ></Alert
        ><Alert
          v-if="actionError && state.tab.value !== 'connection'"
          variant="destructive"
          ><AlertDescription>{{ actionError }}</AlertDescription></Alert
        ><ChannelsQueryBody
          v-if="connectionId"
          :pending="initialization.isPending.value"
          :error="
            initialization.error.value
              ? channelErrorMessage(initialization.error.value)
              : null
          "
          :has-data="!!initialization.data.value"
          :empty="false"
          empty-title=""
          empty-description=""
          @retry="initialization.refetch()"
          ><ChannelInitializationCard
            v-if="initialization.data.value"
            :run="initialization.data.value"
            :can-start="
              active && connection.data.value?.verificationStatus === 'verified'
            "
            :pending="pending"
            @start="startInitialization" /></ChannelsQueryBody
        ><Tabs
          :model-value="state.tab.value"
          @update:model-value="(value) => changeTab(String(value))"
          ><TabsList
            ><TabsTrigger value="publications">Публикации</TabsTrigger
            ><TabsTrigger value="connection">Подключение</TabsTrigger></TabsList
          ><TabsContent value="publications" class="flex flex-col gap-4"
            ><template v-if="connectionId"
              ><ContentUpdatesHistory
                :items="history.data.value ?? []"
                @open="openContentResult" />
              <div
                v-if="contentSelection.length"
                class="flex flex-wrap items-center gap-3"
              >
                <span class="text-muted-foreground text-sm"
                  >Выбрано публикаций: {{ contentSelection.length }}</span
                ><Button
                  variant="outline"
                  :disabled="catalogBusy"
                  @click="openContentUpdate(contentSelection)"
                  >Сравнить тексты выбранных</Button
                ><Button variant="ghost" @click="contentSelection = []"
                  >Снять выбор</Button
                >
              </div>
              <PublicationIdentitySummary
                v-if="publications.data.value?.identitySummary"
                :key="connectionId"
                :summary="publications.data.value.identitySummary"
                @filter="state.setIdentity" />
              <PublicationsToolbar
                :identity-label="
                  publications.data.value?.identitySummary?.label
                "
                :identity-status="state.identityStatus.value"
                :identity-key="state.identityKey.value"
                :search="state.search.value"
                :stock-status="state.stockStatus.value"
                :binding-status="state.bindingStatus.value"
                @change="state.setFilters" /><ChannelsQueryBody
                :pending="publications.isPending.value"
                :error="
                  publications.error.value
                    ? channelErrorMessage(publications.error.value)
                    : null
                "
                :has-data="!!publications.data.value"
                :empty="!publications.data.value?.items.length"
                :empty-title="
                  state.search.value ||
                  state.stockStatus.value ||
                  state.bindingStatus.value ||
                  state.identityStatus.value ||
                  state.identityKey.value
                    ? 'Публикации не найдены'
                    : 'Публикаций пока нет'
                "
                :empty-description="
                  state.search.value ||
                  state.stockStatus.value ||
                  state.bindingStatus.value ||
                  state.identityStatus.value ||
                  state.identityKey.value
                    ? 'Измените поисковый запрос или фильтры.'
                    : 'Они появятся после проверки доступа и первой загрузки.'
                "
                @retry="publications.refetch()"
                ><PublicationsList
                  :identity-label="
                    publications.data.value?.identitySummary?.label
                  "
                  @duplicates="(key) => state.setIdentity('duplicate', key)"
                  :can-update="
                    (platform.data.value?.capabilities.includes(
                      'preview_content_update',
                    ) ??
                      false) &&
                    active &&
                    connection.data.value?.verificationStatus === 'verified'
                  "
                  :selected-ids="contentSelection"
                  @select="selectContent"
                  @update-texts="
                    (publication) => openContentUpdate([publication.id])
                  "
                  :archived="channel.data.value.isArchived"
                  :busy="catalogBusy"
                  :can-import="
                    platform.data.value?.capabilities.includes(
                      'read_publication_details',
                    ) ?? false
                  "
                  @bind="
                    (publication) => openCatalogAction('bind', publication)
                  "
                  @draft="
                    (publication) => openCatalogAction('draft', publication)
                  "
                  @unbind="
                    (publication) => openCatalogAction('unbind', publication)
                  "
                  @open-catalog="openCatalogItem"
                  :items="
                    publications.data.value?.items ?? []
                  " /></ChannelsQueryBody
              ><ChannelsPagination
                v-if="publications.data.value"
                :page="state.page.value"
                :total="publications.data.value.total"
                :limit="20"
                :pending="publications.isFetching.value"
                @change="state.setPage" /></template
            ><Alert v-else
              ><AlertTitle>Настройте подключение</AlertTitle
              ><AlertDescription
                >После сохранения настроек проверка доступа и загрузка начнутся
                автоматически.<Button
                  variant="outline"
                  size="sm"
                  @click="changeTab('connection')"
                  >Настроить подключение</Button
                ></AlertDescription
              ></Alert
            ></TabsContent
          ><TabsContent value="connection"
            ><Card
              ><CardHeader
                ><CardTitle>Подключение к источнику</CardTitle
                ><CardDescription
                  >Один канал подключается к одному магазину. Данные доступа
                  хранятся защищённо.</CardDescription
                ></CardHeader
              ><CardContent class="flex flex-col gap-5"
                ><ChannelsQueryBody
                  :pending="
                    platform.isPending.value ||
                    references.isPending.value ||
                    (!!connectionId && connection.isPending.value)
                  "
                  :error="
                    platform.error.value ||
                    references.error.value ||
                    connection.error.value
                      ? channelErrorMessage(
                          platform.error.value ??
                            references.error.value ??
                            connection.error.value,
                        )
                      : null
                  "
                  :has-data="
                    !!platform.data.value &&
                    !!references.data.value &&
                    (!connectionId || !!connection.data.value)
                  "
                  :empty="false"
                  empty-title=""
                  empty-description=""
                  @retry="
                    platform.refetch();
                    references.refetch();
                    connectionId && connection.refetch();
                  "
                  ><template v-if="platform.data.value && references.data.value"
                    ><Alert v-if="!platformSupported(platform.data.value)"
                      ><AlertTitle
                        >Форма плагина пока не поддерживается</AlertTitle
                      ><AlertDescription
                        >Обновите Console для работы с этой версией
                        конфигурации.</AlertDescription
                      ></Alert
                    ><template v-else
                      ><section
                        v-if="connection.data.value"
                        class="flex flex-col gap-3"
                      >
                        <div class="flex flex-wrap items-center gap-2">
                          <ChannelStatusBadge
                            :status="connection.data.value.verificationStatus"
                            :paused="connection.data.value.isPaused"
                          /><Button
                            v-if="!connection.data.value.isPaused"
                            variant="outline"
                            size="sm"
                            :disabled="
                              pending ||
                              dirty ||
                              channel.data.value.isArchived ||
                              connection.data.value.verificationStatus ===
                                'queued'
                            "
                            @click="connectionAction('verify')"
                            >Проверить доступ</Button
                          ><Button
                            variant="outline"
                            size="sm"
                            :disabled="
                              pending || dirty || channel.data.value.isArchived
                            "
                            @click="
                              connectionAction(
                                connection.data.value.isPaused
                                  ? 'resume'
                                  : 'pause',
                              )
                            "
                            >{{
                              connection.data.value.isPaused
                                ? "Продолжить работу"
                                : "Приостановить"
                            }}</Button
                          >
                        </div>
                        <p
                          v-if="connection.data.value.reasonCode"
                          class="text-destructive text-sm"
                        >
                          {{ reasonLabel(connection.data.value.reasonCode) }}
                        </p>
                        <p
                          v-if="connection.data.value.isPaused"
                          class="text-muted-foreground text-sm"
                        >
                          Новые обращения к источнику приостановлены. Настройки
                          можно сохранить локально.
                        </p>
                      </section>
                      <ConnectionForm
                        :key="connectionId || 'new'"
                        :platform="platform.data.value"
                        :connection="connection.data.value"
                        :references="references.data.value"
                        :revision="revision"
                        :pending="pending"
                        :disabled="channel.data.value.isArchived"
                        :error="actionError"
                        :save-sequence="saveSequence"
                        @submit="save"
                        @dirty="
                          dirty = $event
                        " /></template></template></ChannelsQueryBody></CardContent></Card></TabsContent></Tabs></template
    ></ChannelsQueryBody>
    <BindPublicationDialog
      v-if="catalogAction === 'bind' && selectedPublication"
      :key="selectedPublication.id"
      :title="selectedPublication.title ?? selectedPublication.externalId"
      :items="
        candidates.data.value?.publicationId === selectedId &&
        candidates.data.value?.locale === candidateState.locale.value
          ? candidates.data.value
          : undefined
      "
      :locale="candidateState.locale.value"
      :locales="references.data.value?.locales ?? []"
      :page="candidateState.page.value"
      :loading="candidates.isFetching.value"
      :pending="catalogBusy"
      :error="
        candidates.error.value
          ? channelErrorMessage(candidates.error.value)
          : null
      "
      :action-error="catalogActionError"
      @close="closeCatalogAction"
      @search="candidateState.setSearch"
      @locale="candidateState.setLocale"
      @page="candidateState.setPage"
      @retry="candidates.refetch()"
      @bind="bindSelected"
    />
    <UnbindPublicationDialog
      v-if="catalogAction === 'unbind' && selectedPublication"
      :title="selectedPublication.title ?? selectedPublication.externalId"
      :pending="catalogBusy"
      :error="catalogActionError"
      @close="closeCatalogAction"
      @confirm="unbindSelected"
    />
  </main>
</template>
