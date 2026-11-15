<script setup lang="ts">
import { Button } from "@/components/ui/button";
import type { ReceiptExecutionHistory } from "../../model/receipt-posting.types";
defineProps<{
  page: ReceiptExecutionHistory | undefined;
  loading: boolean;
  error: string;
  pending: boolean;
}>();
const emit = defineEmits<{
  retry: [];
  open: [id: string];
  posting: [id: string];
  page: [offset: number];
}>();
</script>
<template>
  <section
    class="w-full max-w-5xl shrink-0 rounded-lg border bg-card p-4"
    aria-label="История приёмок"
  >
    <h2 class="mb-3 text-lg font-semibold">История приёмок</h2>
    <p v-if="loading && !page" role="status">Загрузка истории…</p>
    <p v-if="error" role="alert" class="text-sm text-destructive">
      {{ error
      }}<Button variant="outline" :disabled="pending" @click="emit('retry')"
        >Повторить историю</Button
      >
    </p>
    <template v-if="page"
      ><p v-if="!page.items.length" class="text-sm text-muted-foreground">
        Фактических приёмок пока нет.
      </p>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead>
            <tr>
              <th class="p-2">Проведено</th>
              <th class="p-2">Строк</th>
              <th class="p-2">Версия после</th>
              <th class="p-2">Факты</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in page.items"
              :key="item.executionId"
              class="border-t"
            >
              <td class="whitespace-nowrap p-2">
                {{ new Date(item.postedAt).toLocaleString() }}
              </td>
              <td class="p-2">{{ item.lineCount }}</td>
              <td class="p-2">{{ item.documentVersionAfter }}</td>
              <td class="flex gap-2 p-2">
                <Button
                  variant="outline"
                  size="sm"
                  @click="emit('open', item.executionId)"
                  >Открыть исполнение</Button
                ><Button
                  variant="outline"
                  size="sm"
                  @click="emit('posting', item.postingId)"
                  >Ledger</Button
                >
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="mt-3 flex items-center justify-between gap-2">
        <Button
          variant="outline"
          size="sm"
          :disabled="pending || !page.offset"
          @click="emit('page', Math.max(0, page.offset - page.limit))"
          >Назад</Button
        ><span class="text-xs"
          >{{ page.total ? page.offset + 1 : 0 }}–{{
            Math.min(page.offset + page.limit, page.total)
          }}
          из {{ page.total }}</span
        ><Button
          variant="outline"
          size="sm"
          :disabled="pending || page.offset + page.limit >= page.total"
          @click="emit('page', page.offset + page.limit)"
          >Далее</Button
        >
      </div></template
    >
  </section>
</template>
