# API response schemas

Hand-written [Zod](https://zod.dev) schemas describing the shape of every API
response the frontend consumes.

## Why these exist

Every response goes through one of these schemas at the network boundary
(`apiClient.get/post/put`). If the backend changes a response shape without
telling the frontend, you get a `ValidationError` **at the fetch site** —
naming the path and the offending fields — instead of an `undefined` access
deep in the render tree, far from the real cause.

In short: contract drift surfaces as a clear, located error, not a mystery
crash.

## How to keep them in sync

These are written by hand, so they can drift from the backend's OpenAPI
contract. When the backend changes a response:

1. Run `npm run gen-types` to regenerate `ui/src/types/api.ts` from OpenAPI.
2. Eyeball the diff in `api.ts`.
3. Update the matching schema here to match.

## Convention

- **Response** schemas live here (`ui/src/schemas/api/`) — output validation.
- **Form input** schemas live in `ui/src/schemas/` (e.g. `tickets.ts`) — input
  validation. They serve a different concern and have different shapes.

Each schema exports both the schema and its inferred type
(`z.infer<typeof schema>`) so call sites can use either.
