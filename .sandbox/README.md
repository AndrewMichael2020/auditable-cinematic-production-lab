# Project sandbox

The repository-local sandbox interface is `scripts/sandbox`.

It uses the machine's Codex OrbStack harness so that:

- the host checkout is mounted read-only;
- work happens in a disposable container-local copy;
- runtime network access is disabled;
- `.env` and provider credentials are not mounted;
- build products, ledgers, and generated media are discarded with the container.

Build the reusable runtime image once:

```bash
./scripts/sandbox build
```

Run the complete Python and FFmpeg test suite:

```bash
./scripts/sandbox test
```

Run the dry-run policy and manifest validations:

```bash
./scripts/sandbox validate
```

Run another command in the disposable project copy:

```bash
./scripts/sandbox run 'python -m video_gen.cli --help'
```

The `run` command accepts one quoted shell command. It intentionally does not
provide network access or persistent output mounts. Local model inference will
use a separate, explicit profile with read-only model weights and a narrowly
scoped writable run directory; do not broaden this default sandbox for it.
