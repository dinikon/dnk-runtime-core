import type { ProductSection } from "./product.types";
import type { UpdateItemRequest } from "../api/catalog.dto";

export interface DraftEntry {
  value: UpdateItemRequest;
  token: number;
  error: string;
}
export interface AutosaveState {
  entries: Partial<Record<ProductSection, DraftEntry>>;
  pending: boolean;
  paused: boolean;
  error: string;
  held: boolean;
}
export interface SaveFailure {
  message: string;
  fields: Partial<Record<ProductSection, string>>;
}

/** Одна очередь PATCH: подтверждение снимка никогда не сбрасывает более новый ввод. */
export class ProductAutosave {
  private timer: ReturnType<typeof setTimeout> | undefined;
  private active: Promise<void> | null = null;
  private token = 0;
  private epoch = 0;
  private changedAt = 0;

  constructor(
    readonly state: AutosaveState,
    private send: (value: UpdateItemRequest) => Promise<unknown>,
    private acknowledge: (sections: ProductSection[]) => Promise<void>,
    private failure: (error: unknown) => SaveFailure,
    private delay = 800,
  ) {}

  stage(section: ProductSection, value: UpdateItemRequest, error = ""): void {
    this.state.entries[section] = {
      value: JSON.parse(JSON.stringify(value)) as UpdateItemRequest,
      token: ++this.token,
      error,
    };
    this.changedAt = Date.now();
    this.schedule();
  }

  private schedule(): void {
    clearTimeout(this.timer);
    if (this.state.paused || this.state.held) return;
    this.timer = setTimeout(
      () => void this.drain(),
      Math.max(0, this.changedAt + this.delay - Date.now()),
    );
  }

  async flush(): Promise<void> {
    clearTimeout(this.timer);
    if (this.active) await this.active;
    await this.drain(true);
  }

  retry(): void {
    this.state.paused = false;
    this.state.error = "";
    void this.flush();
  }

  resume(): void {
    this.state.held = false;
    this.schedule();
  }

  cancel(): void {
    clearTimeout(this.timer);
    this.epoch++;
    this.state.entries = {};
    this.state.pending = false;
    this.state.paused = false;
    this.state.error = "";
    this.state.held = false;
  }

  private async drain(force = false): Promise<void> {
    if (this.active) return this.active;
    if (this.state.paused || this.state.held) return;
    const work = async () => {
      const epoch = this.epoch;
      while (!this.state.paused && !this.state.held && epoch === this.epoch) {
        const entries = Object.entries(this.state.entries).filter(
          ([, entry]) => entry && !entry.error,
        ) as [ProductSection, DraftEntry][];
        if (!entries.length) break;
        if (!force && Date.now() < this.changedAt + this.delay) break;
        const value: UpdateItemRequest = Object.assign(
          {},
          ...entries.map(([, entry]) => entry.value),
        );
        this.state.pending = true;
        this.state.error = "";
        try {
          await this.send(value);
          if (epoch !== this.epoch) return;
          for (const [section, sent] of entries) {
            if (this.state.entries[section]?.token === sent.token)
              delete this.state.entries[section];
          }
          await this.acknowledge(entries.map(([section]) => section));
        } catch (error) {
          if (epoch !== this.epoch) return;
          const failure = this.failure(error);
          let recognized = false;
          for (const [section, message] of Object.entries(failure.fields) as [
            ProductSection,
            string,
          ][]) {
            const sent = entries.find(([name]) => name === section)?.[1];
            const current = this.state.entries[section];
            if (sent) {
              recognized = true;
              if (current?.token === sent.token) current.error = message;
            }
          }
          if (!recognized) {
            this.state.paused = true;
            this.state.error = failure.message;
          }
        } finally {
          if (epoch === this.epoch) this.state.pending = false;
        }
      }
    };
    this.active = work();
    try {
      await this.active;
    } finally {
      this.active = null;
      if (
        Object.values(this.state.entries).some((entry) => entry && !entry.error)
      )
        this.schedule();
    }
  }
}
