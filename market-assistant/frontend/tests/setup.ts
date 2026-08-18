import "@testing-library/jest-dom/vitest";

// jsdom implements its own AbortController/AbortSignal (WHATWG DOM classes,
// used for e.g. XHR abort semantics) which shadow Node's globals in this test
// environment. Node's built-in fetch/Request (undici) validates `signal`
// against ITS OWN AbortSignal class, so a signal from jsdom's AbortController
// fails that check with "Expected signal to be an instance of AbortSignal".
// React Router's data router (createBrowserRouter/createMemoryRouter) builds
// a Request for every client-side navigation using the ambient
// AbortController, so any real navigation (e.g. our RequireAuth guard's
// <Navigate>, or useNavigate()) trips this and silently aborts. Tests don't
// need real request cancellation, so make Request tolerant: retry without an
// incompatible signal instead of throwing.
const NativeRequest = globalThis.Request;
globalThis.Request = new Proxy(NativeRequest, {
  construct(target, args: [RequestInfo | URL, RequestInit?]) {
    const [input, init] = args;
    try {
      return new target(input, init);
    } catch (err) {
      if (init && "signal" in init && err instanceof TypeError) {
        const rest = { ...init };
        delete rest.signal;
        return new target(input, rest);
      }
      throw err;
    }
  },
}) as typeof Request;

// jsdom in this environment ships without a localStorage implementation, so the
// persisted theme store has nowhere to write. Provide a minimal in-memory one.
if (typeof globalThis.localStorage === "undefined") {
  const store = new Map<string, string>();
  const localStorageMock: Storage = {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (key) => (store.has(key) ? store.get(key)! : null),
    key: (index) => Array.from(store.keys())[index] ?? null,
    removeItem: (key) => void store.delete(key),
    setItem: (key, value) => void store.set(key, String(value)),
  };
  Object.defineProperty(globalThis, "localStorage", {
    value: localStorageMock,
    configurable: true,
  });
}
