<script setup lang="ts">
import { computed } from "vue";
import type { OfferConversion } from "../model/types";
const props = defineProps<{
  value?: OfferConversion | null;
  kind?: "purchase_price" | "rrp";
  label?: string;
}>();
const money = computed(() => props.value?.[props.kind ?? "purchase_price"]);
const reasons: Record<string, string> = {
  policy_not_configured: "Валюты не настроены",
  functional_currency_not_configured: "Нет основной валюты на дату",
  currency_disabled: "Валюта отключена",
  currency_not_found: "Валюта отсутствует в справочнике",
  exchange_rate_not_found: "Нет курса",
  cross_rate_unavailable: "Нет общего курса на дату",
  legacy_state: "Снимок не записывался",
};
</script>

<template>
  <div class="flex flex-col gap-1 text-xs text-muted-foreground">
    <span
      v-if="money"
      :title="`${money.conversion.provider_code} · ${money.conversion.derivation} · курс ${money.conversion.rate} · дата ${money.conversion.effective_date}`"
    >
      {{ label ? `${label}: ` : "" }}{{ money.converted.amount }}
      {{ money.converted.currency }}
    </span>
    <span v-else-if="value?.status === 'unavailable'"
      >{{ label ? `${label}: ` : ""
      }}{{ reasons[value.error_code ?? ""] ?? "Пересчёт недоступен" }}</span
    >
    <span v-if="money" class="font-normal"
      >Курс на {{ money.conversion.effective_date }}</span
    >
  </div>
</template>
