export { default as ContactPointsWidget } from "./ui/ContactPointsWidget.vue";
export { default as PhoneContactPointsField } from "./ui/PhoneContactPointsField.vue";
export { default as EmailContactPointsField } from "./ui/EmailContactPointsField.vue";
export { useContactPointLabels } from "./model/use-labels-query";
export {
  mapContactPoint,
  contactPointPayload,
  contactPointServerErrors,
  validateContactPoints,
} from "./model/validation";
export type {
  ContactPointArrays,
  ContactPointDraft,
  ContactPointLabel,
  ContactPointDto,
  ContactPointErrors,
  ContactPointKind,
} from "./model/types";
