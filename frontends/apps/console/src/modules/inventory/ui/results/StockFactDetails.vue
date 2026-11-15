<script setup lang="ts">
import {
  stockDocumentStatusLabel,
  stockStatusLabel,
} from "../../model/stock-accounting.constants";
import { ref } from "vue";
import StockTrackingColumnsControl from "./StockTrackingColumnsControl.vue";
import { Button } from "@/components/ui/button";
import type {
  GetStockExecutionDetailsResult,
  GetStockPostingDetailsResult,
} from "../../model/stock-accounting.types";
import type { StockAccountingTarget } from "../../model/stock-accounting-navigation";
defineProps<{
  fact: GetStockExecutionDetailsResult | GetStockPostingDetailsResult;
}>();
const emit = defineEmits<{
  navigate: [target: StockAccountingTarget];
  movements: [];
}>();
const trackingColumns = ref({ lot: false, serial: false });
</script>
<template>
  <div class="flex min-w-0 shrink-0 flex-col gap-5">
    <section class="rounded-lg border p-4">
      <h2 class="text-lg font-semibold">Основание движения</h2>
      <p class="mt-2 text-sm">
        {{ fact.warehouseCode }} — {{ fact.warehouseName }} ·
        {{ fact.ownerName ?? fact.ownerId }}
      </p>
      <p class="mt-1 text-sm">
        Версия документа при исполнении: {{ fact.documentVersionAtExecution }}.
        Текущая версия: {{ fact.documentCurrentVersion }} ·
        {{ stockDocumentStatusLabel(fact.documentCurrentStatus) }}
      </p>
      <p class="mt-1 text-xs text-muted-foreground">
        Количество зафиксировано в факте. Подписи справочников показаны
        актуальные; исторические значения отмечены отдельно.
      </p>
      <div class="mt-3 flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          @click="
            emit('navigate', {
              kind: 'document',
              id: fact.documentId,
              operationType: fact.operationType,
            })
          "
          >Документ</Button
        ><span>→</span
        ><Button
          variant="outline"
          @click="emit('navigate', { kind: 'execution', id: fact.executionId })"
          >Исполнение</Button
        ><span>→</span
        ><Button
          v-if="fact.postingId"
          variant="outline"
          @click="emit('navigate', { kind: 'posting', id: fact.postingId })"
          >Проводка</Button
        ><span>→</span
        ><Button variant="outline" @click="emit('movements')"
          >Записи журнала</Button
        >
      </div>
    </section>
    <section class="min-w-0 rounded-lg border p-4">
      <h2 class="mb-3 text-lg font-semibold">Фактические строки</h2>
      <StockTrackingColumnsControl
        class="mb-3"
        :columns="trackingColumns"
        @change="trackingColumns = $event"
      />
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead>
            <tr>
              <th class="p-2">SKU</th>
              <th class="p-2">Исходный ввод</th>
              <th class="p-2">В базовой единице</th>
              <th class="p-2">Адрес / состояние</th>
              <th v-if="trackingColumns.lot" class="p-2">Партия</th>
              <th v-if="trackingColumns.serial" class="p-2">Серия</th>
              <th class="p-2">Связи Ledger</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="line in fact.lines" :key="line.id" class="border-t">
              <td class="p-2">
                <Button
                  variant="link"
                  class="h-auto p-0"
                  @click="
                    emit('navigate', { kind: 'item', id: line.inventoryItemId })
                  "
                  >{{ line.sku }}</Button
                ><span class="block text-xs text-muted-foreground"
                  >В документе: {{ line.skuAtDocument }}</span
                ><span
                  v-if="line.skuAtReceipt && line.skuAtReceipt !== line.sku"
                  class="block text-xs"
                  >При приёмке: {{ line.skuAtReceipt }}</span
                >
              </td>
              <td class="whitespace-nowrap p-2">
                {{ line.sourceQuantity }} {{ line.sourceUom
                }}<span class="block text-xs"
                  >Коэффициент {{ line.factorToBase }}</span
                >
              </td>
              <td class="whitespace-nowrap p-2">
                {{ line.quantity }} {{ line.baseUom }}
              </td>
              <td class="p-2">
                {{ line.locationCode
                }}<span v-if="line.destinationLocationCode">
                  → {{ line.destinationLocationCode }}</span
                >
                ·
                {{ stockStatusLabel(line.stockStatus) }}
              </td>
              <td v-if="trackingColumns.lot" class="p-2">
                <Button
                  v-if="line.lotId"
                  variant="link"
                  class="h-auto p-0"
                  @click="
                    emit('navigate', {
                      kind: 'lot',
                      id: line.lotId,
                      itemId: line.inventoryItemId,
                    })
                  "
                  >{{ line.lotNumber }}</Button
                ><span v-else>—</span>
              </td>
              <td v-if="trackingColumns.serial" class="p-2">
                <Button
                  v-if="line.serialId"
                  variant="link"
                  class="h-auto p-0"
                  @click="
                    emit('navigate', {
                      kind: 'serial',
                      id: line.serialId,
                      itemId: line.inventoryItemId,
                    })
                  "
                  >{{ line.serialNumber }}</Button
                ><span v-else>—</span
                ><span
                  v-if="
                    line.serialNumberAtReceipt &&
                    line.serialNumberAtReceipt !== line.serialNumber
                  "
                  class="block text-xs"
                  >При приёмке: {{ line.serialNumberAtReceipt }}</span
                >
              </td>
              <td class="p-2 text-xs">
                <span
                  v-if="line.destinationLocationCode"
                  class="block break-all"
                  >Расход: {{ line.sourceLedgerEntryId }}<br />Приход:
                  {{ line.destinationLedgerEntryId }}</span
                >
                <span
                  class="block max-w-44 break-all"
                  v-for="id in line.ledgerEntryIds"
                  :key="id"
                  >{{ id }}</span
                >
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section class="min-w-0 rounded-lg border p-4">
      <h2 class="mb-3 text-lg font-semibold">Записи Ledger</h2>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead>
            <tr>
              <th class="p-2">Запись</th>
              <th class="p-2">Изменение</th>
              <th class="p-2">Фактических строк</th>
              <th class="p-2">Позиция</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in fact.ledger" :key="entry.id" class="border-t">
              <td class="max-w-48 break-all p-2 font-mono text-xs">
                {{ entry.id }}
              </td>
              <td class="whitespace-nowrap p-2">
                {{ entry.quantityDelta.startsWith("-") ? "" : "+"
                }}{{ entry.quantityDelta }} {{ entry.baseUom }}
              </td>
              <td class="p-2">{{ entry.executionLineIds.length }}</td>
              <td class="p-2">
                <Button
                  variant="outline"
                  size="sm"
                  @click="
                    emit('navigate', { kind: 'position', id: entry.positionId })
                  "
                  >Открыть позицию</Button
                >
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section class="rounded-lg border p-4">
      <h2 class="mb-3 text-lg font-semibold">Исходные стоимостные основания</h2>
      <p v-if="!fact.costs.length" class="text-sm text-muted-foreground">
        Стоимость неизвестна. Ноль не подставляется.
      </p>
      <ul class="space-y-3">
        <li
          v-for="cost in fact.costs"
          :key="cost.id"
          class="rounded-md border p-3 text-sm"
        >
          <strong>{{ cost.amount }} {{ cost.currency }}</strong>
          <p>
            {{ cost.basisKind }} ·
            {{ cost.sourceReference ?? "Без внешней ссылки" }}
          </p>
          <p>
            {{
              cost.allocations.length
                ? "Распределено по фактическим строкам"
                : "Не распределено"
            }}
          </p>
          <ul>
            <li
              v-for="allocation in cost.allocations"
              :key="allocation.executionLineId"
            >
              Строка
              {{
                fact.lines.findIndex(
                  (line) => line.id === allocation.executionLineId,
                ) + 1
              }}: {{ allocation.amount }} {{ cost.currency }}
            </li>
          </ul>
        </li>
      </ul>
      <p class="mt-3 text-xs text-muted-foreground">
        Это исходные суммы, а не рассчитанная себестоимость. Для строк без
        основания стоимость неизвестна.
      </p>
    </section>
  </div>
</template>
