<script setup lang="ts">
import { useSaveFunnel } from "../model/funnel.mutations";
import { computed, ref, watch, onScopeDispose } from "vue";
import { useRoute, useRouter, onBeforeRouteLeave } from "vue-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Field, FieldLabel, FieldGroup } from "@/components/ui/field";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
} from "@/components/ui/alert-dialog";
import { getApiErrorMessage, getApiErrorStatus } from "@/app/providers/http";
import { useFunnel, useFunnelScope } from "../model/funnel.queries";
import {
  acknowledgeFunnelDraft,
  defaultFunnelDraft,
  validateFunnelDraft,
} from "../model/funnel.draft";
import type { FunnelDetails, FunnelDraft } from "../model/funnel.types";
import StageEditor from "../ui/StageEditor.vue";
const route = useRoute(),
  router = useRouter(),
  id = computed(() => String(route.params.id ?? "")),
  detail = useFunnel(id),
  saveMutation = useSaveFunnel(),
  scope = useFunnelScope();
function empty(): FunnelDraft {
  return defaultFunnelDraft(
    route.query.type === "crm.deal" ? "crm.deal" : "crm.lead",
  );
}
const revision = ref<number>(),
  conflict = ref(false);
const draft = ref(empty()),
  baseline = ref(JSON.stringify(draft.value)),
  error = ref(""),
  guard = ref(false);
const savedDefinition = ref<FunnelDetails>();
const success = ref("");
const confirmRemoval = ref(false);
const confirmedDeletion = ref(false);
const removedStages = computed(
  () =>
    savedDefinition.value?.stages.filter(
      (s) => !draft.value.stages.some((v) => v.id === s.id),
    ) ?? [],
);
const dirty = computed(() => JSON.stringify(draft.value) !== baseline.value);
let leaveResolve: ((v: boolean) => void) | null = null;
let leaveSaving = false;
function apply(v: FunnelDetails): void {
  savedDefinition.value = JSON.parse(JSON.stringify(v)) as FunnelDetails;
  revision.value = v.revision;
  conflict.value = false;
  draft.value = {
    name: v.name,
    modelKey: v.modelKey,
    stages: v.stages.map((s) => ({
      id: s.id,
      clientKey: s.id,
      name: s.name,
      color: s.color,
      kind: s.kind,
    })),
  };
  baseline.value = JSON.stringify(draft.value);
}
watch(
  () => detail.data.value,
  (v) => {
    if (v && !dirty.value) apply(v);
  },
  { immediate: true },
);
async function save(): Promise<boolean> {
  if (saveMutation.isPending.value) return false;
  const validation = validateFunnelDraft(draft.value);
  if (validation) {
    error.value = validation;
    return false;
  }
  if (conflict.value) {
    error.value = "Сначала сверьте актуальное определение.";
    return false;
  }
  if (removedStages.value.length && !confirmedDeletion.value) {
    confirmRemoval.value = true;
    return false;
  }
  confirmedDeletion.value = false;
  error.value = "";
  const context = scope.value.join("|");
  try {
    const sent = JSON.parse(JSON.stringify(draft.value)) as FunnelDraft;
    success.value = "";
    const result = await saveMutation.mutateAsync({
      id: id.value || undefined,
      draft: sent,
      revision: revision.value,
    });
    if (context !== scope.value.join("|")) return false;
    const acknowledged = acknowledgeFunnelDraft(
      draft.value,
      sent,
      result.stageIdMap,
    );
    draft.value = acknowledged.current;
    baseline.value = JSON.stringify(acknowledged.baseline);
    revision.value = result.revision;
    if (!id.value) {
      leaveSaving = true;
      await router.replace("/funnels/" + result.id);
      leaveSaving = false;
    }
    const fresh = await detail.refetch();
    if (context !== scope.value.join("|")) return false;
    if (fresh.data) {
      savedDefinition.value = JSON.parse(
        JSON.stringify(fresh.data),
      ) as FunnelDetails;
      if (!dirty.value && fresh.data.revision === result.revision)
        apply(fresh.data);
      if (fresh.data.revision !== result.revision) conflict.value = true;
    }
    success.value =
      "Воронка сохранена. Перемещено карточек: " + result.movedCardsCount + ".";
    return true;
  } catch (e) {
    if (context !== scope.value.join("|")) return false;
    if (getApiErrorStatus(e) === 409) {
      conflict.value = true;
      await detail.refetch();
    }
    error.value = getApiErrorMessage(e, "Не удалось выполнить действие.");
    return false;
  }
}
function mergeServer(): void {
  const value = detail.data.value;
  if (!value) return;
  const serverIds = new Set(value.stages.map((s) => s.id));
  if (draft.value.stages.some((s) => s.id && !serverIds.has(s.id))) {
    error.value =
      "В черновике есть стадии, удалённые на сервере. Удалите их из черновика перед принятием версии.";
    return;
  }
  const knownIds = new Set(
    savedDefinition.value?.stages.map((s) => s.id) ?? [],
  );
  const serverAdditions = value.stages.filter((s) => !knownIds.has(s.id));
  if (
    serverAdditions.some((s) => !draft.value.stages.some((v) => v.id === s.id))
  ) {
    error.value =
      "На сервере добавлены стадии. Загрузите серверное определение или добавьте их в черновик кнопкой ниже.";
    return;
  }
  savedDefinition.value = JSON.parse(JSON.stringify(value)) as FunnelDetails;
  revision.value = value.revision;
  conflict.value = false;
  error.value = "";
  success.value =
    "Актуальная версия принята. Проверьте черновик перед сохранением.";
}
function addServerStages(): void {
  const knownIds = new Set(
    savedDefinition.value?.stages.map((s) => s.id) ?? [],
  );
  for (const stage of detail.data.value?.stages ?? []) {
    if (
      !knownIds.has(stage.id) &&
      !draft.value.stages.some((s) => s.id === stage.id)
    ) {
      draft.value.stages.push({
        id: stage.id,
        clientKey: stage.id,
        name: stage.name,
        color: stage.color,
        kind: stage.kind,
      });
    }
  }
  const order = { in_progress: 0, won: 1, lost: 2 };
  draft.value.stages.sort((a, b) => order[a.kind] - order[b.kind]);
}
async function confirmSave(): Promise<void> {
  confirmRemoval.value = false;
  confirmedDeletion.value = true;
  if (await save()) finishLeave(true);
}
function reset() {
  if (detail.data.value) apply(detail.data.value);
  else {
    draft.value = empty();
    baseline.value = JSON.stringify(draft.value);
  }
}
function finishLeave(value: boolean) {
  guard.value = false;
  leaveResolve?.(value);
  leaveResolve = null;
}
async function saveLeave() {
  if (await save()) finishLeave(true);
}
onBeforeRouteLeave(() => {
  if (leaveSaving || !dirty.value) return true;
  if (saveMutation.isPending.value) return false;
  return new Promise<boolean>((resolve) => {
    leaveResolve = resolve;
    guard.value = true;
  });
});
function beforeUnload(e: BeforeUnloadEvent) {
  if (dirty.value) {
    e.preventDefault();
    e.returnValue = "";
  }
}
window.addEventListener("beforeunload", beforeUnload);
onScopeDispose(() => {
  window.removeEventListener("beforeunload", beforeUnload);
  leaveResolve?.(false);
});
watch(
  () => scope.value.join("|"),
  () => {
    finishLeave(false);
    saveMutation.reset();
    draft.value = empty();
    baseline.value = JSON.stringify(draft.value);
    error.value = "";
    savedDefinition.value = undefined;
    revision.value = undefined;
    conflict.value = false;
    confirmRemoval.value = false;
    success.value = "";
  },
);
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-auto pb-6">
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <Button variant="ghost" @click="router.push('/funnels')"
          >← Воронки</Button
        >
        <h1 class="text-2xl font-semibold">
          {{ id ? "Настройка воронки" : "Новая воронка" }}
        </h1>
        <p class="text-sm text-muted-foreground">
          {{
            dirty ? "Есть несохранённые изменения" : "Все изменения сохранены"
          }}
        </p>
      </div>
      <div class="flex gap-2">
        <Button
          variant="outline"
          :disabled="!dirty || saveMutation.isPending.value"
          @click="reset"
          >Отменить изменения</Button
        ><Button
          :disabled="saveMutation.isPending.value || !dirty"
          @click="save"
          >{{
            saveMutation.isPending.value ? "Сохраняем…" : "Сохранить"
          }}</Button
        >
      </div>
    </header>
    <Alert v-if="success"
      ><AlertDescription role="status">{{ success }}</AlertDescription></Alert
    >
    <Alert v-if="error || detail.error.value" variant="destructive"
      ><AlertDescription role="alert"
        >{{
          error ||
          getApiErrorMessage(
            detail.error.value,
            "Не удалось выполнить действие.",
          )
        }}<Button v-if="id" variant="outline" @click="detail.refetch()"
          >Обновить серверные данные</Button
        ></AlertDescription
      ></Alert
    >
    <section
      v-if="conflict && detail.data.value"
      class="flex flex-col gap-3 rounded-lg border p-4"
    >
      <h2 class="font-semibold">
        Сверка с актуальной версией {{ detail.data.value.revision }}
      </h2>
      <p>{{ detail.data.value.name }}</p>
      <ol class="list-inside list-decimal">
        <li v-for="stage in detail.data.value.stages" :key="stage.id">
          {{ stage.name }} · {{ stage.color }}
        </li>
      </ol>
      <p class="text-sm text-muted-foreground">
        Ваш черновик сохранён ниже. Примите актуальную версию после сверки;
        изменения не объединяются автоматически; удаления из вашего черновика
        сохраняются.
      </p>
      <Button variant="outline" @click="addServerStages"
        >Добавить новые серверные стадии для сверки</Button
      >
      <Button variant="outline" @click="reset"
        >Загрузить серверное определение</Button
      >
      <Button variant="outline" @click="mergeServer"
        >Я сверил изменения — принять версию</Button
      >
    </section>
    <Skeleton v-if="id && detail.isPending.value" class="h-56 w-full" />
    <form
      v-else-if="!id || detail.data.value"
      class="flex max-w-3xl flex-col gap-6"
      @submit.prevent="save"
    >
      <FieldGroup
        ><Field
          ><FieldLabel for="funnel-name">Название воронки *</FieldLabel
          ><Input
            id="funnel-name"
            v-model="draft.name"
            required
            maxlength="150"
            :disabled="saveMutation.isPending.value" /></Field
        ><Field
          ><FieldLabel for="funnel-type">Тип карточек</FieldLabel
          ><NativeSelect
            id="funnel-type"
            v-model="draft.modelKey"
            :disabled="!!id || saveMutation.isPending.value"
            ><option value="crm.lead">Лиды</option>
            <option value="crm.deal">Сделки</option></NativeSelect
          ></Field
        ></FieldGroup
      ><StageEditor
        v-model="draft.stages"
        :disabled="saveMutation.isPending.value"
      />
    </form>
    <AlertDialog :open="confirmRemoval" @update:open="confirmRemoval = $event">
      <AlertDialogContent
        ><AlertDialogHeader
          ><AlertDialogTitle
            >Удалить стадии и перенести карточки?</AlertDialogTitle
          >
          <AlertDialogDescription
            >Все карточки удаляемых стадий перейдут в «{{
              draft.stages[0]?.name
            }}». Количества приведены по последнему
            чтению.</AlertDialogDescription
          ></AlertDialogHeader
        >
        <ul class="flex flex-col gap-2">
          <li v-for="stage in removedStages" :key="stage.id">
            {{ stage.name }} — {{ stage.cardsCount }} карточек
          </li>
        </ul>
        <AlertDialogFooter
          ><Button variant="outline" @click="confirmRemoval = false"
            >Отмена</Button
          ><Button @click="confirmSave"
            >Сохранить и перенести</Button
          ></AlertDialogFooter
        >
      </AlertDialogContent>
    </AlertDialog>
    <AlertDialog :open="guard"
      ><AlertDialogContent
        ><AlertDialogHeader
          ><AlertDialogTitle>Несохранённые изменения</AlertDialogTitle
          ><AlertDialogDescription
            >Сохранить определение воронки перед уходом?</AlertDialogDescription
          ></AlertDialogHeader
        ><AlertDialogFooter
          ><Button variant="outline" @click="finishLeave(false)"
            >Остаться</Button
          ><Button variant="secondary" @click="finishLeave(true)"
            >Отбросить изменения</Button
          ><Button :disabled="saveMutation.isPending.value" @click="saveLeave"
            >Сохранить</Button
          ></AlertDialogFooter
        ></AlertDialogContent
      ></AlertDialog
    >
  </div>
</template>
