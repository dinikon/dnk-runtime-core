<script setup lang="ts">
import { returnDirectionLabel } from "../../model/return-origin.types";
import type { ReturnExecutionResult } from "../../model/return-execution-result.types";
defineProps<{ result: ReturnExecutionResult }>();
</script>
<template>
  <section
    class="min-w-0 rounded-lg border p-4"
    aria-label="Первоначальный результат возврата"
  >
    <h2 class="text-lg font-semibold">Первоначальный результат возврата</h2>
    <p class="mt-2 text-sm font-medium">
      {{ returnDirectionLabel(result.direction) }}
    </p>
    <p class="mt-3 whitespace-pre-wrap break-words text-sm">
      <strong>Причина возврата:</strong> {{ result.reason }}
    </p>
    <p class="mt-2 text-sm text-muted-foreground">
      Исторические количества до и после этого возврата. Текущий остаток может
      отличаться.
    </p>
    <p class="mt-1 text-sm">
      Версия документа: {{ result.versionBefore }} → {{ result.versionAfter }}
    </p>
    <div class="mt-3 overflow-x-auto">
      <table class="w-full text-left text-sm">
        <thead>
          <tr>
            <th class="p-2">Позиция</th>
            <th class="p-2">Было</th>
            <th class="p-2">Изменение</th>
            <th class="p-2">Стало</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="position in result.positions"
            :key="position.id"
            class="border-t"
          >
            <td class="max-w-48 break-all p-2 font-mono text-xs">
              {{ position.id }}
            </td>
            <td class="whitespace-nowrap p-2">
              {{ position.before }} {{ position.baseUom }}
            </td>
            <td class="whitespace-nowrap p-2">
              {{ position.delta }} {{ position.baseUom }}
            </td>
            <td class="whitespace-nowrap p-2">
              {{ position.after }} {{ position.baseUom }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
