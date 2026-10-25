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
import type { Funnel, FunnelDraft } from "../model/funnel.types";
import StageEditor from "../ui/StageEditor.vue";
const route = useRoute(),
  router = useRouter(),
  id = computed(() => String(route.params.id ?? "")),
  detail = useFunnel(id),
  saveMutation = useSaveFunnel(),
  scope = useFunnelScope();
function empty(): FunnelDraft {
  return {
    name: "",
    modelKey: route.query.type === "crm.deal" ? "crm.deal" : "crm.lead",
    stages: [
      { clientKey: crypto.randomUUID(), name: "Новая", color: "neutral" },
    ],
  };
}
const revision = ref<number>(),
  conflict = ref(false);
const draft = ref(empty()),
  baseline = ref(JSON.stringify(draft.value)),
  error = ref(""),
  guard = ref(false);
const dirty = computed(() => JSON.stringify(draft.value) !== baseline.value);
let leaveResolve: ((v: boolean) => void) | null = null;
let leaveSaving = false;
function apply(v: Funnel) {
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
async function save() {
  if (saveMutation.isPending.value) return false;
  if (
    !draft.value.name.trim() ||
    draft.value.stages.some((s) => !s.name.trim())
  ) {
    error.value = "Заполните название воронки и всех стадий.";
    return false;
  }
  error.value = "";
  const context = scope.value.join("|");
  try {
    const result = await saveMutation.mutateAsync({
      id: id.value || undefined,
      draft: JSON.parse(JSON.stringify(draft.value)) as FunnelDraft,
      revision: revision.value,
    });
    if (context !== scope.value.join("|")) return false;
    baseline.value = JSON.stringify(draft.value);
    if (!id.value) {
      leaveSaving = true;
      await router.replace("/funnels/" + result.id);
      leaveSaving = false;
    }
    const fresh = await detail.refetch();
    if (fresh.data) apply(fresh.data);
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
function mergeServer() {
  const value = detail.data.value;
  if (!value) return;
  const known = new Set(draft.value.stages.map((s) => s.id));
  draft.value.stages.push(
    ...value.stages
      .filter((s) => !known.has(s.id))
      .map((s) => ({
        id: s.id,
        clientKey: s.id,
        name: s.name,
        color: s.color,
      })),
  );
  revision.value = value.revision;
  conflict.value = false;
  error.value =
    "Актуальная версия принята. Проверьте черновик перед сохранением.";
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
      class="space-y-3 rounded-lg border p-4"
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
        новые серверные стадии будут добавлены в конец черновика.
      </p>
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
