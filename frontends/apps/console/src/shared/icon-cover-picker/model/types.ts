import type { HTMLAttributes } from "vue";

export interface IconCoverPickerLabels {
  triggerAriaLabel: string;
  title: string;
  description: string;
  backgroundLabel: string;
  backgroundInputAriaLabel: string;
  validationMessage: string;
  cancel: string;
  confirm: string;
  useBackgroundLabel: (color: string) => string;
}

export interface IconCoverPickerProps {
  modelValue: string;
  background: string;
  invalid?: boolean;
  disabled?: boolean;
  triggerClass?: HTMLAttributes["class"];
  iconClass?: HTMLAttributes["class"];
  labels?: Partial<IconCoverPickerLabels>;
  backgroundPresets?: string[];
}
