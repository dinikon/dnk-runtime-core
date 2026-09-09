<script setup lang="ts">
import { computed, ref, watch, nextTick } from "vue";
import { Eye, EyeOff } from "@lucide/vue";
import { Field, FieldLabel, FieldDescription, FieldError } from "@dnk/ui/components/field";
import { Input } from "@dnk/ui/components/input";
import { InputGroup, InputGroupInput, InputGroupAddon, InputGroupButton } from "@dnk/ui/components/input-group";
import { Checkbox } from "@dnk/ui/components/checkbox";
import { RadioGroup, RadioGroupItem } from "@dnk/ui/components/radio-group";
import { NativeSelect, NativeSelectOption } from "@dnk/ui/components/native-select";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@dnk/ui/components/input-otp";
import { Textarea } from "@dnk/ui/components/textarea";
import type { FieldSchema } from "./types";

const props = defineProps<{ field: FieldSchema }>();
const value = ref(String(props.field.value ?? ""));
const checked = ref(props.field.checked ?? Boolean(props.field.value));
const visible = ref(false);
const invalid = computed(() => props.field.errors.length > 0);
const checkbox = props.field.type === "checkbox";
const id = String(props.field.attrs.id);
const controlId = checkbox ? `${id}_control` : id;
const attrs = computed(() => ({ ...props.field.attrs, id: controlId,
  "aria-invalid": invalid.value || undefined,
  "aria-describedby": [props.field.attrs["aria-describedby"], props.field.help && `${id}_helptext`, invalid.value && `${id}_error`].filter(Boolean).join(" ") || undefined,
}));
const otp = props.field.type === "otp";
watch(checked, async () => {
  await nextTick();
  // Native allauth listeners (including the recovery-code save confirmation)
  // subscribe to this input's change event, not to Vue's model update.
  document.getElementById(id)?.dispatchEvent(new Event("change", { bubbles: true }));
});
</script>

<template>
  <Field :data-invalid="invalid || undefined" :data-disabled="field.attrs.disabled || undefined" :orientation="checkbox ? 'horizontal' : 'vertical'">
    <template v-if="checkbox">
      <!-- The native checkbox keeps allauth's .checked contract and form value. -->
      <input v-bind="field.attrs" v-model="checked" type="checkbox" :value="field.checkboxValue ?? 'on'" hidden>
      <Checkbox :id="controlId" v-model="checked" :disabled="Boolean(field.attrs.disabled)" :aria-describedby="attrs['aria-describedby']" />
      <FieldLabel :for="controlId" class="min-h-11 cursor-pointer">{{ field.label }}</FieldLabel>
    </template>
    <template v-else>
      <FieldLabel :for="controlId">{{ field.label }}</FieldLabel>
      <InputGroup v-if="field.type === 'password'">
        <InputGroupInput v-bind="attrs" v-model="value" :type="visible ? 'text' : 'password'" />
        <InputGroupAddon align="inline-end">
          <InputGroupButton class="size-11" type="button" :aria-label="visible ? 'Скрыть пароль' : 'Показать пароль'" :aria-pressed="visible" @click="visible = !visible">
            <EyeOff v-if="visible" /><Eye v-else />
          </InputGroupButton>
        </InputGroupAddon>
      </InputGroup>
      <InputOTP v-else-if="otp" v-bind="attrs" v-model="value" :maxlength="6" pattern="^[0-9]*$" inputmode="numeric" autocomplete="one-time-code">
        <InputOTPGroup><InputOTPSlot v-for="index in 6" :key="index" :index="index - 1" /></InputOTPGroup>
      </InputOTP>
      <Textarea v-else-if="field.type === 'textarea'" v-bind="attrs" v-model="value" />
      <NativeSelect v-else-if="field.type === 'select'" v-bind="attrs" v-model="value" class="w-full">
        <NativeSelectOption v-for="option in field.options" :key="option.value" :value="option.value">{{ option.label }}</NativeSelectOption>
      </NativeSelect>
      <RadioGroup v-else-if="field.type === 'radio-group'" v-bind="attrs" v-model="value">
        <Field v-for="(option, index) in field.options" :key="option.value" orientation="horizontal">
          <RadioGroupItem :id="`${id}_${index}`" :value="option.value" />
          <FieldLabel :for="`${id}_${index}`" class="min-h-11 cursor-pointer">{{ option.label }}</FieldLabel>
        </Field>
      </RadioGroup>
      <Input v-else v-bind="attrs" v-model="value" :type="field.type" />
    </template>
    <FieldDescription v-if="field.help" :id="`${id}_helptext`">{{ field.help }}</FieldDescription>
    <FieldError v-if="invalid" :id="`${id}_error`" role="alert" :errors="field.errors.map(message => ({ message }))" />
  </Field>
</template>
