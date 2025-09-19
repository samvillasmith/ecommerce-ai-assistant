/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-require-imports */
// jest.setup.ts
import "@testing-library/jest-dom";
import "whatwg-fetch"; // fetch, Request, Response, Headers for jsdom
import "web-streams-polyfill/polyfill";


// TextEncoder/TextDecoder for MSW/interceptors
import { TextEncoder, TextDecoder } from "util";

if (!(global as any).TextEncoder) (global as any).TextEncoder = TextEncoder as any;

if (!(global as any).TextDecoder) (global as any).TextDecoder = TextDecoder as any;

// Web Streams (TransformStream/ReadableStream/WritableStream) for MSW v2
try {
  // Node 16+/18+ provides these via 'stream/web'
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { TransformStream, ReadableStream, WritableStream } = require("stream/web");
  if (!(global as any).TransformStream) (global as any).TransformStream = TransformStream;
  if (!(global as any).ReadableStream) (global as any).ReadableStream = ReadableStream;
  if (!(global as any).WritableStream) (global as any).WritableStream = WritableStream;
} catch {
  // noop — if not available, tests may still pass unless a stream is used
}

// BroadcastChannel for MSW v2 (used internally)
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { BroadcastChannel } = require("worker_threads");
  if (BroadcastChannel && !(global as any).BroadcastChannel) {
    (global as any).BroadcastChannel = BroadcastChannel;
  }
} catch {
  class BCShim {
    name: string;
    onmessage: ((ev: MessageEvent) => void) | null = null;
    constructor(name: string) { this.name = name; }
    postMessage(_msg: unknown) {}
    close() {}
    addEventListener() {}
    removeEventListener() {}
  }
  if (!(global as any).BroadcastChannel) {
    (global as any).BroadcastChannel = BCShim as any;
  }
}

// jsdom doesn't implement element.scrollTo — polyfill for tests
if (!(HTMLElement.prototype as any).scrollTo) {
  Object.defineProperty(HTMLElement.prototype, "scrollTo", {
    value: () => {},
    writable: true,
  });
}
