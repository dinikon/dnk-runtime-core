<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import type {
  FeedAccessMode,
  FeedAccessToken,
  FeedAccessTokenStatus,
  IssuedFeedAccessToken,
  IssueFeedAccessToken,
} from "../../model/feed-access.types";

const props = defineProps<{
  mode: FeedAccessMode;
  tokens?: FeedAccessToken[];
  loading: boolean;
  loadError: string;
  actionError: string;
  busy: boolean;
  issued?: IssuedFeedAccessToken;
  downloadUrl?: string;
}>();
const emit = defineEmits<{
  changeMode: [mode: FeedAccessMode];
  issue: [input: IssueFeedAccessToken];
  revoke: [tokenId: string];
  copy: [value: string];
  dismiss: [];
  retry: [];
}>();
const mode = ref(props.mode);
const name = ref("");
const expiresAt = ref("");
const expiryError = ref("");
const statusLabels: Record<FeedAccessTokenStatus, string> = {
  ACTIVE: "Действует",
  EXPIRED: "Истёк",
  REVOKED: "Отозван",
};
watch(() => props.mode, (value) => { mode.value = value; });
watch(() => props.issued?.id, (id) => {
  if (id) {
    name.value = "";
    expiresAt.value = "";
    expiryError.value = "";
  }
});
const tokenLink = computed(() => {
  if (!props.downloadUrl || !props.issued) return undefined;
  const url = new URL(props.downloadUrl);
  url.searchParams.set("token", props.issued.token);
  return url.toString();
});

function issue(): void {
  if (props.busy || props.issued || !name.value.trim()) return;
  const date = expiresAt.value ? new Date(expiresAt.value) : null;
  if (date && !(date.getTime() > Date.now())) {
    expiryError.value = "Укажите дату и время позже текущих.";
    return;
  }
  emit("issue", { name: name.value.trim(), expiresAt: date?.toISOString() ?? null });
}
function revoke(item: FeedAccessToken): void {
  if (window.confirm(`Отозвать токен «${item.name}»?`)) emit("revoke", item.id);
}
function dateLabel(value: string): string {
  return new Date(value).toLocaleString("ru-RU");
}
</script>

<template>
  <section class="grid min-w-0 gap-4 rounded-lg border p-4" aria-labelledby="feed-access-title">
    <h2 id="feed-access-title" class="font-medium">Доступ к фиду</h2>
    <form class="flex flex-wrap items-end gap-2" @submit.prevent="emit('changeMode', mode)">
      <label class="grid gap-1 text-sm">
        Режим доступа
        <select v-model="mode" class="rounded-md border bg-background p-2" :disabled="busy">
          <option value="PUBLIC">Публичный</option>
          <option value="PRIVATE">Приватный</option>
        </select>
      </label>
      <Button type="submit" variant="outline" :disabled="busy || mode === props.mode">
        Сохранить доступ
      </Button>
    </form>
    <p v-if="mode === 'PUBLIC' && props.mode === 'PRIVATE'" class="text-sm text-muted-foreground">
      После сохранения любой получатель ссылки сможет скачать файл.
    </p>
    <p v-if="actionError" role="alert" class="text-sm text-destructive">{{ actionError }}</p>

    <div class="grid min-w-0 gap-3 border-t pt-4">
      <h3 class="text-sm font-medium">Токены доступа</h3>
      <form class="flex min-w-0 flex-wrap items-end gap-2" @submit.prevent="issue">
        <label class="grid min-w-0 flex-1 gap-1 text-sm">
          Название интеграции
          <Input v-model="name" maxlength="120" :disabled="busy || !!issued" required />
        </label>
        <label class="grid max-w-full min-w-0 gap-1 text-sm">
          Срок действия (по желанию)
          <Input
            v-model="expiresAt"
            type="datetime-local"
            :disabled="busy || !!issued"
            :aria-invalid="!!expiryError"
            @update:model-value="expiryError = ''"
          />
        </label>
        <Button type="submit" :disabled="busy || !!issued || !name.trim()">Выпустить токен</Button>
      </form>
      <p v-if="expiryError" role="alert" class="text-sm text-destructive">{{ expiryError }}</p>

      <div v-if="issued" class="grid min-w-0 gap-2 rounded-md border p-3" aria-label="Новый токен">
        <p class="font-medium">Токен «{{ issued.name }}» выпущен</p>
        <p class="text-sm text-muted-foreground">
          Скопируйте {{ tokenLink ? "ссылку" : "токен" }} сейчас. Секрет показывается один раз.
        </p>
        <Input :model-value="tokenLink ?? issued.token" :aria-label="tokenLink ? 'Ссылка с токеном' : 'Секрет токена'" readonly />
        <div class="flex flex-wrap gap-2">
          <Button type="button" size="sm" @click="emit('copy', tokenLink ?? issued.token)">
            {{ tokenLink ? "Скопировать ссылку с токеном" : "Скопировать токен" }}
          </Button>
          <Button type="button" size="sm" variant="ghost" @click="emit('dismiss')">Готово</Button>
        </div>
      </div>

      <div v-if="loadError" class="flex flex-wrap items-center gap-2">
        <p role="alert" class="text-sm text-destructive">{{ loadError }}</p>
        <Button type="button" size="sm" variant="outline" :disabled="busy" @click="emit('retry')">Повторить</Button>
      </div>
      <p v-else-if="loading && !tokens" role="status" class="text-sm text-muted-foreground">Загрузка токенов…</p>
      <p v-else-if="!tokens?.length" class="text-sm text-muted-foreground">Токены пока не выпущены.</p>
      <ul v-if="tokens?.length" class="divide-y rounded-md border">
        <li v-for="item in tokens" :key="item.id" class="flex min-w-0 flex-wrap items-center justify-between gap-2 p-3">
          <div class="grid min-w-0 gap-1">
            <div class="flex min-w-0 flex-wrap items-center gap-2">
              <p class="min-w-0 break-all text-sm font-medium">{{ item.name }}</p>
              <Badge variant="secondary">{{ statusLabels[item.status] }}</Badge>
            </div>
            <p class="text-xs text-muted-foreground">
              {{ item.expiresAt ? `До ${dateLabel(item.expiresAt)}` : "Без срока действия" }}
            </p>
          </div>
          <Button
            v-if="item.status !== 'REVOKED'"
            type="button"
            variant="outline"
            size="sm"
            :disabled="busy"
            :aria-label="`Отозвать токен ${item.name}`"
            @click="revoke(item)"
          >Отозвать</Button>
        </li>
      </ul>
    </div>
  </section>
</template>
