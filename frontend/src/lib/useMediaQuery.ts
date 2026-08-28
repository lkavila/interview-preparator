import { useSyncExternalStore } from "react";

/** Reactive `window.matchMedia`. Used where a layout change is not expressible
 * as a CSS breakpoint alone — e.g. Matching has to stop measuring DOM geometry
 * for its connector lines once the two columns stack. */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const mql = window.matchMedia(query);
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    },
    () => window.matchMedia(query).matches,
    () => true // SSR / no-window: assume the wide layout
  );
}

/** Tailwind's `sm` breakpoint. */
export const useIsWide = () => useMediaQuery("(min-width: 640px)");
