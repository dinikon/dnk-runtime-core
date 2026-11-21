import type {
  PackagingTypeCreateValues,
  PackagingTypeFieldErrors,
} from "./packaging-type.types.ts";
export function validatePackagingType(
  values: PackagingTypeCreateValues,
): PackagingTypeFieldErrors {
  const errors: PackagingTypeFieldErrors = {};
  if (!values.code.trim()) errors.code = "Укажите код типа тары.";
  if (!values.name.trim()) errors.name = "Укажите название типа тары.";
  return errors;
}
