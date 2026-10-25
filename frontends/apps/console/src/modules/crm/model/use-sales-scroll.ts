import { onBeforeRouteLeave } from "vue-router";
import { onMounted, onBeforeUnmount, nextTick, type Ref } from "vue";
interface ScrollPosition {
  root: number;
  board: number;
  left: number;
}
const positions = new Map<string, ScrollPosition>();
export function useSalesScroll(
  element: Ref<HTMLElement | null>,
  key: () => string,
): void {
  let resize: ResizeObserver | null = null,
    mutation: MutationObserver | null = null,
    timer: ReturnType<typeof setTimeout> | undefined;
  const disconnect = () => {
    resize?.disconnect();
    mutation?.disconnect();
    clearTimeout(timer);
  };
  onMounted(async () => {
    await nextTick();
    const target = element.value,
      saved = positions.get(key());
    if (!target || !saved) return;
    const restore = () => {
      target.scrollTop = saved.root;
      const board = target.querySelector<HTMLElement>('[aria-label="Канбан"]');
      if (board) {
        board.scrollTop = saved.board;
        board.scrollLeft = saved.left;
      }
      if (
        target.scrollHeight - target.clientHeight >= saved.root &&
        (!saved.board ||
          (board && board.scrollHeight - board.clientHeight >= saved.board))
      )
        disconnect();
    };
    resize = new ResizeObserver(restore);
    resize.observe(target);
    mutation = new MutationObserver(restore);
    mutation.observe(target, { childList: true, subtree: true });
    timer = setTimeout(disconnect, 1500);
    restore();
  });
  onBeforeRouteLeave(() => {
    const target = element.value;
    if (!target) return;
    const board = target.querySelector<HTMLElement>('[aria-label="Канбан"]');
    positions.set(key(), {
      root: target.scrollTop,
      board: board?.scrollTop ?? 0,
      left: board?.scrollLeft ?? 0,
    });
    if (positions.size > 100) positions.delete(positions.keys().next().value!);
  });
  onBeforeUnmount(disconnect);
}
