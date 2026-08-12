/** Tiny pub/sub so any API response carrying `new_badges` can trigger the
 * badge toast in the layout without prop drilling. */

type Listener = (badgeKeys: string[]) => void;

const listeners = new Set<Listener>();

export function onBadgesEarned(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function emitBadgesEarned(badgeKeys: string[] | undefined): void {
  if (!badgeKeys || badgeKeys.length === 0) return;
  listeners.forEach((l) => l(badgeKeys));
}
