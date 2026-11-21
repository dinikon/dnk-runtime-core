import type { Channel } from "./channel.types";

export function shouldPoll(channel: Channel): boolean {
  return channel.verification.status === "pending" && !channel.recoveryRequired;
}
