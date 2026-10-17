export type ProductPreset = "simple" | "service";

export interface ProductCreationState {
  pending: boolean;
  preset: ProductPreset | null;
  createdId: string | null;
  uncertain: boolean;
  error: string;
}

export function productCreationState(): ProductCreationState {
  return {
    pending: false,
    preset: null,
    createdId: null,
    uncertain: false,
    error: "",
  };
}

/** Один явный POST; сбой открытия уже созданной карточки повторяет только переход. */
export class ProductCreation {
  private epoch = 0;

  constructor(
    readonly state: ProductCreationState,
    private readonly send: (virtual: boolean) => Promise<{ id: string }>,
    private readonly open: (id: string) => Promise<void>,
    private readonly failure: (error: unknown) => {
      message: string;
      uncertain: boolean;
    },
  ) {}

  cancel(): void {
    this.epoch++;
    Object.assign(this.state, productCreationState());
  }

  async create(preset: ProductPreset): Promise<void> {
    if (this.state.pending || this.state.uncertain) return;
    const epoch = this.epoch;
    this.state.pending = true;
    this.state.error = "";
    this.state.preset = this.state.createdId ? this.state.preset : preset;
    try {
      if (!this.state.createdId) {
        const result = await this.send(preset === "service");
        if (epoch !== this.epoch) return;
        this.state.createdId = result.id;
      }
      await this.open(this.state.createdId);
    } catch (error: unknown) {
      if (epoch !== this.epoch) return;
      const failure = this.failure(error);
      this.state.uncertain = !this.state.createdId && failure.uncertain;
      this.state.error = this.state.createdId
        ? "Товар создан, но карточку не удалось открыть. Повторите открытие."
        : this.state.uncertain
          ? "Ответ не получен. Товар мог быть создан. Проверьте каталог перед новой попыткой."
          : failure.message;
    } finally {
      if (epoch === this.epoch) this.state.pending = false;
    }
  }
}
