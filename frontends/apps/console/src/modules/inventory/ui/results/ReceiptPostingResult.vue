<script setup lang="ts">
import { Button } from "@/components/ui/button";
import type { ReceiptPostingResult } from "../../model/receipt-posting.types";
defineProps<{ result: ReceiptPostingResult }>();
const emit = defineEmits<{ document: []; execution: []; posting: [] }>();
const statuses: Record<string, string> = {
  COMPLETED: "Выполнен",
  PARTIALLY_EXECUTED: "Частично выполнен",
};
</script>
<template>
  <div class="flex w-full max-w-6xl shrink-0 flex-col gap-5">
    <section class="rounded-lg border bg-card p-4">
      <h2 class="mb-3 text-lg font-semibold">Результат приёмки</h2>
      <p class="mb-4 rounded-md bg-muted p-3 text-sm">
        Товар принят на склад. Движение и результат операции сохранены в
        истории.
      </p>
      <dl class="grid gap-4 text-sm sm:grid-cols-2">
        <div>
          <dt class="text-muted-foreground">Документ после операции</dt>
          <dd>
            {{ statuses[result.documentStatus] ?? result.documentStatus }} ·
            версия {{ result.documentVersionAfter }}
          </dd>
        </div>
        <div>
          <dt class="text-muted-foreground">Склад / владелец</dt>
          <dd>
            {{ result.warehouseCode }} — {{ result.warehouseName }}<br />{{
              result.ownerName ?? result.ownerId
            }}
          </dd>
        </div>
        <div>
          <dt class="text-muted-foreground">Исполнение</dt>
          <dd class="break-all font-mono text-xs">{{ result.executionId }}</dd>
        </div>
        <div>
          <dt class="text-muted-foreground">Проводка</dt>
          <dd class="break-all font-mono text-xs">{{ result.postingId }}</dd>
        </div>
        <div>
          <dt class="text-muted-foreground">Проведено</dt>
          <dd>
            <time :datetime="result.postedAt">{{
              new Date(result.postedAt).toLocaleString()
            }}</time>
          </dd>
        </div>
      </dl>
      <div class="mt-4 flex flex-wrap gap-2">
        <Button variant="outline" @click="emit('document')">Документ</Button
        ><Button variant="outline" @click="emit('execution')">Исполнение</Button
        ><Button variant="outline" @click="emit('posting')"
          >Проводка и движения</Button
        >
      </div>
    </section>
    <section class="min-w-0 rounded-lg border bg-card p-4">
      <h2 class="mb-3 text-lg font-semibold">Фактически принято</h2>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead>
            <tr>
              <th class="p-2">SKU</th>
              <th class="p-2">Исходный ввод</th>
              <th class="p-2">Базовое количество</th>
              <th class="p-2">Локация</th>
              <th class="p-2">Партия / экземпляр</th>
              <th class="p-2">Состояние</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="line in result.lines" :key="line.id" class="border-t">
              <td class="whitespace-nowrap p-2 font-mono">{{ line.sku }}</td>
              <td class="whitespace-nowrap p-2">
                {{ line.sourceQuantity }} {{ line.sourceUom }}
              </td>
              <td class="whitespace-nowrap p-2">
                {{ line.quantity }} {{ line.baseUom }}
              </td>
              <td class="p-2">{{ line.locationCode }}</td>
              <td class="whitespace-nowrap p-2">
                {{ line.lotNumber ?? "—" }} / {{ line.serialNumber ?? "—" }}
              </td>
              <td class="p-2">{{ line.stockStatus }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section class="min-w-0 rounded-lg border bg-card p-4">
      <h2 class="mb-3 text-lg font-semibold">Изменение физических позиций</h2>
      <p class="mb-3 text-xs text-muted-foreground">
        Показан результат на момент этой операции. Текущий остаток после
        следующих движений может отличаться.
      </p>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead>
            <tr>
              <th class="p-2">Позиция</th>
              <th class="p-2">До</th>
              <th class="p-2">Дельта</th>
              <th class="p-2">После</th>
              <th class="p-2">Версии</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="position in result.positions"
              :key="position.id"
              class="border-t"
            >
              <td class="p-2 font-mono text-xs">{{ position.id }}</td>
              <td class="whitespace-nowrap p-2">
                {{ position.beforeQuantity }} {{ position.baseUom }}
              </td>
              <td class="whitespace-nowrap p-2">
                +{{ position.delta }} {{ position.baseUom }}
              </td>
              <td class="whitespace-nowrap p-2">
                {{ position.afterQuantity }} {{ position.baseUom }}
              </td>
              <td class="whitespace-nowrap p-2">
                {{ position.beforeVersion }} → {{ position.afterVersion }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section class="min-w-0 rounded-lg border bg-card p-4">
      <h2 class="mb-3 text-lg font-semibold">Журнал движений</h2>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead>
            <tr>
              <th class="p-2">Запись</th>
              <th class="p-2">Позиция</th>
              <th class="p-2">Дельта</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in result.ledger" :key="entry.id" class="border-t">
              <td class="p-2 font-mono text-xs">{{ entry.id }}</td>
              <td class="p-2 font-mono text-xs">{{ entry.positionId }}</td>
              <td class="whitespace-nowrap p-2">
                +{{ entry.quantityDelta }} {{ entry.baseUom }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section class="min-w-0 rounded-lg border bg-card p-4">
      <h2 class="mb-3 text-lg font-semibold">Исходные стоимостные основания</h2>
      <p v-if="!result.costs.length" class="text-sm text-muted-foreground">
        Стоимость неизвестна. Нулевая стоимость не подставлялась.
      </p>
      <ul v-else class="space-y-3">
        <li
          v-for="cost in result.costs"
          :key="cost.id"
          class="rounded-md border p-3 text-sm"
        >
          <p class="font-medium">{{ cost.amount }} {{ cost.currency }}</p>
          <p class="mt-1 text-muted-foreground">
            {{
              cost.basisKind === "MANUAL"
                ? "Ручное основание"
                : "Внешнее основание"
            }}
            · {{ cost.sourceReference ?? "без внешней ссылки" }} ·
            {{
              cost.allocations.length
                ? "Распределено по фактическим строкам"
                : "Не распределено"
            }}
          </p>
          <ul v-if="cost.allocations.length" class="mt-2 space-y-1">
            <li
              v-for="allocation in cost.allocations"
              :key="allocation.executionLineId"
              class="break-all text-xs"
            >
              Строка {{ allocation.executionLineId }}: {{ allocation.amount }}
              {{ cost.currency }}
            </li>
          </ul>
        </li>
      </ul>
      <p class="mt-3 text-xs text-muted-foreground">
        Это исходные коммерческие сведения, а не рассчитанная себестоимость. Для
        строк без стоимостного основания стоимость неизвестна.
      </p>
    </section>
  </div>
</template>
