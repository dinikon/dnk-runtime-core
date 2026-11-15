<script setup lang="ts">
import type { ReturnOrigin } from "../../model/return-origin.types";
import { returnDirectionLabel } from "../../model/return-origin.types";
import { Button } from "@/components/ui/button";
defineProps<{
  origin: ReturnOrigin | undefined;
  loading: boolean;
  error: string;
}>();
const emit = defineEmits<{ create: []; list: []; retry: [] }>();
</script>
<template>
  <section
    class="shrink-0 rounded-lg border p-4"
    aria-label="Возвраты по исполнению"
  >
    <h2 class="text-lg font-semibold">Возвраты по исполнению</h2>
    <p v-if="loading" role="status">Загрузка возвращённого объёма…</p>
    <p v-if="error" role="alert">
      {{ error }}
      <Button variant="outline" @click="emit('retry')">Повторить</Button>
    </p>
    <template v-if="origin && !error">
      <p class="mt-2 text-sm">{{ returnDirectionLabel(origin.direction) }}</p>
      <div class="mt-3 overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead>
            <tr>
              <th class="p-2">SKU / исходная строка</th>
              <th class="p-2">Исходный факт</th>
              <th class="p-2">Возвращено</th>
              <th class="p-2">К возврату</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="line in origin.lines" :key="line.id" class="border-t">
              <td class="p-2">{{ line.sku }} · {{ line.position + 1 }}</td>
              <td class="p-2">{{ line.quantity }} {{ line.baseUom }}</td>
              <td class="p-2">
                {{ line.returnedQuantity }} {{ line.baseUom }}
              </td>
              <td class="p-2">
                {{ line.remainingQuantity }} {{ line.baseUom }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="mt-3 flex flex-wrap gap-2">
        <Button @click="emit('create')">Создать возврат</Button
        ><Button variant="outline" @click="emit('list')"
          >Связанные возвраты</Button
        ><Button variant="outline" @click="emit('retry')"
          >Обновить возвраты</Button
        >
      </div>
    </template>
  </section>
</template>
