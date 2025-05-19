# Generated JavaScript

We're now using TypeScript as the source of truth for frontend code.
The js files in this dir are transpiled from that TypeScript, and so
you **should not** modified the js directly!

Instead, you should make changes to the TypeScript in

```
src/ims/element/typescript
```

then run the `tsc` tool locally, which will automatically update all
the js files in this directory.

Ideally we'll have this automated someday, so that no manual running
of `tsc` and checking-in of generated js files is necessary.
