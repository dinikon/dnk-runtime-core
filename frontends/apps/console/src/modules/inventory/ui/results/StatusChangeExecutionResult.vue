<script setup lang="ts">
import { stockStatusLabel } from "../../model/stock-accounting.constants";
import type { StatusChangeExecutionResult } from "../../model/status-change-execution-result.types";
defineProps<{ result: StatusChangeExecutionResult }>();
</script>
<template>
  <section
    class="min-w-0 rounded-lg border p-4"
    aria-label="Первоначальный результат изменения состояния"
  >
    <h2 class="text-lg font-semibold">
      Первоначальный результат изменения состояния
    </h2>
    <p class="mt-3 whitespace-pre-wrap break-words text-sm">
      <strong>Причина изменения состояния:</strong> {{ result.reason }}
    </p>
    <p class="mt-2 text-sm text-muted-foreground">
      Исторические количества до и после этого изменения состояния. Текущий
      остаток может отличаться.
    </p>
    <p class="mt-1 text-sm">
      Версия документа: {{ result.versionBefore }} → {{ result.versionAfter }}
    </p>
    <ul class="mt-3 space-y-2 text-sm">
      <li
        v-for="line in result.lines"
        :key="line.id"
        class="rounded border p-3"
      >
        {{ line.sku }} · {{ line.locationCode }} ·
        {{ stockStatusLabel(line.stockStatus) }} →
        {{ stockStatusLabel(line.destinationStockStatus) }}<br />{{
          line.quantity
        }}
        {{ line.baseUom }}
        <span v-if="line.lotNumber">· Партия {{ line.lotNumber }}</span>
        <span v-if="line.serialNumber">· Серия {{ line.serialNumber }}</span>
        <p class="mt-1 break-all text-xs text-muted-foreground">
          Расход: {{ line.sourceLedgerEntryId }}<br />Приход:
          {{ line.destinationLedgerEntryId }}
        </p>
      </li>
    </ul>
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
