<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import ChannelsBody from "../ui/ChannelsBody.vue";
import { useChannelsPageState } from "../model/use-channels-page-state";
import { useChannels, useChannelPlatforms } from "../model/channel.queries";
import { channelErrorMessage } from "../model/channel.errors";
const router = useRouter(),
  state = useChannelsPageState();
const query = useChannels(state.filters),
  platforms = useChannelPlatforms();
const error = computed(() =>
  query.error.value || platforms.error.value
    ? channelErrorMessage(query.error.value ?? platforms.error.value)
    : "",
);
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-auto pb-6">
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Каналы продаж</h1>
        <p class="text-sm text-muted-foreground">
          Подключения магазинов и проверка доступа к площадкам.
        </p>
      </div>
      <Button @click="router.push('/channels/new')">Подключить магазин</Button>
    </header>
    <div class="flex flex-wrap gap-3">
      <Input
        :model-value="state.filters.value.search"
        class="max-w-sm"
        aria-label="Поиск каналов"
        placeholder="Название канала"
        @update:model-value="state.setFilter('q', String($event))"
      /><NativeSelect
        :model-value="state.filters.value.platformKind"
        aria-label="Фильтр платформы"
        @update:model-value="state.setFilter('platform', String($event))"
        ><option value="">Все платформы</option>
        <option
          v-for="p in platforms.data.value ?? []"
          :key="p.kind"
          :value="p.kind"
        >
          {{ p.title }}
        </option></NativeSelect
      ><NativeSelect
        :model-value="state.filters.value.status"
        aria-label="Статус проверки"
        @update:model-value="state.setFilter('status', String($event))"
        ><option value="">Все статусы</option>
        <option value="pending">Проверяем</option>
        <option value="verified">Проверено</option>
        <option value="error">Ошибка</option></NativeSelect
      >
    </div>
    <ChannelsBody
      :loading="query.isPending.value || platforms.isPending.value"
      :error="error"
      :items="query.data.value?.items ?? []"
      :platforms="platforms.data.value ?? []"
      @retry="
        query.refetch();
        platforms.refetch();
      "
      @open="router.push('/channels/' + $event)"
    />
    <footer
      v-if="query.data.value"
      class="flex items-center justify-between gap-3"
    >
      <p class="text-sm text-muted-foreground">
        Каналов: {{ query.data.value.total }}
      </p>
      <div class="flex gap-2">
        <Button
          variant="outline"
          :disabled="state.filters.value.offset === 0"
          @click="state.setOffset(state.filters.value.offset - 50)"
          >Назад</Button
        ><Button
          variant="outline"
          :disabled="state.filters.value.offset + 50 >= query.data.value.total"
          @click="state.setOffset(state.filters.value.offset + 50)"
          >Далее</Button
        >
      </div>
    </footer>
  </div>
</template>
