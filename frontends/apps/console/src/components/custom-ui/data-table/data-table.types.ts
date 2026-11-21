export interface DataTableColumn<TKey extends string = string> {
  key: TKey;
  label: string;
  width: number;
  grow?: boolean;
  align?: "left" | "center" | "right";
  pinned?: "start" | "end";
}
