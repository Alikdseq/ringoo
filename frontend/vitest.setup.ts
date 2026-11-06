import "@testing-library/jest-dom";
import { vi } from "vitest";

vi.mock("next/font/google", () => ({
  Geist: () => ({ variable: "--font-geist-sans" }),
  Geist_Mono: () => ({ variable: "--font-geist-mono" }),
  Comfortaa: () => ({ className: "mock-comfortaa" }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
  redirect: vi.fn(),
}));

vi.mock("next/image", () => ({
  __esModule: true,
  default: (props: { alt?: string; src?: string }) => {
    const React = require("react") as typeof import("react");
    return React.createElement("img", {
      src: typeof props.src === "string" ? props.src : "",
      alt: props.alt ?? "",
    });
  },
}));

if (typeof window !== "undefined") {
  window.IntersectionObserver = class IntersectionObserver {
    observe = () => null;
    disconnect = () => null;
    unobserve = () => null;
    root = null;
    rootMargin = "";
    thresholds = [];
  } as unknown as typeof window.IntersectionObserver;

  if (!window.matchMedia) {
    window.matchMedia = (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    });
  }

  Element.prototype.animate = () =>
    ({
      cancel: () => {},
      finish: () => {},
      pause: () => {},
      play: () => {},
      persist: () => {},
      ready: Promise.resolve(),
      replaceState: () => {},
      commitStyles: () => {},
      updatePlaybackRate: () => {},
      id: "",
      currentTime: 0,
      playState: "idle" as AnimationPlayState,
      playbackRate: 1,
      startTime: 0,
      timeline: null,
    }) as unknown as ReturnType<Element["animate"]>;
}

