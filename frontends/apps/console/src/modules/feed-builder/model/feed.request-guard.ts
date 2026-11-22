/** A cancelled request stays obsolete even if the user returns to the same scope. */
export class FeedRequestGuard {
  private active: AbortController | undefined;
  private disposed = false;
  start(): AbortController | undefined {
    if (this.disposed || this.active) return;
    this.active = new AbortController();
    return this.active;
  }
  current(request: AbortController): boolean {
    return !this.disposed && this.active === request;
  }
  finish(request: AbortController): void {
    if (this.current(request)) this.active = undefined;
  }
  cancel(): void {
    this.active?.abort();
    this.active = undefined;
  }
  dispose(): void {
    this.cancel();
    this.disposed = true;
  }
}
