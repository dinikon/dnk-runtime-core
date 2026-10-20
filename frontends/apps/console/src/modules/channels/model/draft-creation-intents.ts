import type { CreateDraftInput, DraftValues } from "./catalog-links.types";
export interface DraftCreationIntent {
  input: CreateDraftInput;
  uncertain: boolean;
}
export function copyDraftValues(values: DraftValues): DraftValues {
  return {
    ...values,
    titles: { ...values.titles },
    ...(values.descriptions
      ? { descriptions: { ...values.descriptions } }
      : {}),
    ...(values.gallery ? { gallery: [...values.gallery] } : {}),
  };
}
export class DraftCreationIntents {
  private readonly intents = new Map<string, DraftCreationIntent>();
  constructor(private readonly key: () => string = () => crypto.randomUUID()) {}
  get(publicationId: string): DraftCreationIntent | undefined {
    const value = this.intents.get(publicationId);
    return value
      ? {
          input: {
            ...value.input,
            values: copyDraftValues(value.input.values),
          },
          uncertain: value.uncertain,
        }
      : undefined;
  }
  prepare(
    publicationId: string,
    observedRevision: number,
    values: DraftValues,
  ): CreateDraftInput {
    const previous = this.get(publicationId);
    if (previous?.uncertain) return previous.input;
    const input = {
      publicationId,
      observedRevision,
      requestKey: this.key(),
      values: copyDraftValues(values),
    };
    this.intents.set(publicationId, { input, uncertain: false });
    return { ...input, values: copyDraftValues(input.values) };
  }
  uncertain(publicationId: string): void {
    const value = this.intents.get(publicationId);
    if (value) value.uncertain = true;
  }
  complete(publicationId: string): void {
    this.intents.delete(publicationId);
  }
  unresolved(): string[] {
    return [...this.intents.entries()]
      .filter(([, intent]) => intent.uncertain)
      .map(([id]) => id);
  }
  clear(): void {
    this.intents.clear();
  }
}
