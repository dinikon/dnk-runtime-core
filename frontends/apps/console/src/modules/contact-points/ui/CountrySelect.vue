<script setup lang="ts">
import { computed, ref } from "vue";
import {
  getCountries,
  getCountryCallingCode,
  type CountryCode,
} from "libphonenumber-js/max";
import { ChevronsUpDown } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import {
  Combobox,
  ComboboxAnchor,
  ComboboxTrigger,
  ComboboxInput,
  ComboboxList,
  ComboboxGroup,
  ComboboxItem,
  ComboboxEmpty,
  ComboboxViewport,
} from "@/components/ui/combobox";
const props = defineProps<{
  modelValue?: CountryCode;
  disabled?: boolean;
  id: string;
  invalid?: boolean;
  describedBy?: string;
}>();
const emit = defineEmits<{ "update:modelValue": [value: CountryCode] }>();
const search = ref("");
const names = new Intl.DisplayNames(["ru"], { type: "region" });
function flag(code: string) {
  return String.fromCodePoint(
    ...[...code].map((char) => 127397 + char.charCodeAt(0)),
  );
}
const countries = getCountries()
  .map((code) => ({
    code,
    name: names.of(code) ?? code,
    dial: "+" + getCountryCallingCode(code),
    flag: flag(code),
  }))
  .sort((a, b) => a.name.localeCompare(b.name, "ru"));
const selected = computed(() =>
  countries.find((item) => item.code === props.modelValue),
);
const filtered = computed(() =>
  countries.filter((item) =>
    `${item.name} ${item.code} ${item.dial}`
      .toLowerCase()
      .includes(search.value.toLowerCase()),
  ),
);
</script>
<template>
  <Combobox
    :model-value="modelValue"
    :disabled="disabled"
    :ignore-filter="true"
    @update:model-value="emit('update:modelValue', $event as CountryCode)"
    @update:open="search = ''"
  >
    <ComboboxAnchor class="w-auto" as-child>
      <ComboboxTrigger as-child>
        <Button
          :id="id"
          type="button"
          variant="ghost"
          size="sm"
          :disabled="disabled"
          :aria-invalid="invalid"
          :aria-describedby="describedBy"
          :aria-label="`Страна телефона: ${selected?.name ?? 'выберите'}`"
        >
          <span aria-hidden="true">{{ selected?.flag }}</span
          ><span>{{ selected?.dial ?? "Страна" }}</span
          ><ChevronsUpDown data-icon="inline-end" />
        </Button>
      </ComboboxTrigger>
    </ComboboxAnchor>
    <ComboboxList class="w-72 max-w-[calc(100vw-2rem)]" align="start">
      <ComboboxInput
        v-model="search"
        placeholder="Страна или код…"
        aria-label="Поиск страны"
      />
      <ComboboxEmpty>Страна не найдена.</ComboboxEmpty>
      <ComboboxViewport class="max-h-60 overflow-y-auto">
        <ComboboxGroup>
          <ComboboxItem
            v-for="country in filtered"
            :key="country.code"
            :value="country.code"
          >
            <span aria-hidden="true">{{ country.flag }}</span
            ><span>{{ country.name }}</span
            ><span class="ml-auto text-muted-foreground">{{
              country.dial
            }}</span>
          </ComboboxItem>
        </ComboboxGroup>
      </ComboboxViewport>
    </ComboboxList>
  </Combobox>
</template>
