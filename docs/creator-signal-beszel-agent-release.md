# Creator Signal Beszel release

`creator-signal/main` is the standalone Creator Signal reconciliation branch for the upstream `henrygd/beszel` `v0.18.7` source line. Upstream remains pullable through the `upstream` remote; Creator Signal changes stay on `creator-signal/*` branches and are reconciled there before release.

**Creator Signal CI** is the sole downstream publication workflow. Dispatch it from `creator-signal/main` with the immutable tag `v0.18.7-cs.1`. It checks that the tag points to the selected source revision, publishes the GoReleaser binary packages to the GitHub release, and publishes these multi-platform images:

- `ghcr.io/creator-signal/fork-henrygd-beszel/beszel:v0.18.7-cs.1`
- `ghcr.io/creator-signal/fork-henrygd-beszel/beszel-agent:v0.18.7-cs.1` and `:v0.18.7-cs.1-alpine`
- `ghcr.io/creator-signal/fork-henrygd-beszel/beszel-agent-nvidia:v0.18.7-cs.1`
- `ghcr.io/creator-signal/fork-henrygd-beszel/beszel-agent-intel:v0.18.7-cs.1`

Each image also has an exact source-SHA tag and BuildKit SBOM/provenance attestations. The GitHub release contains the binary packages, checksums, and `creator-signal-release-manifest.json`, which records the upstream baseline, exact source revision, and immutable image digests. No host, Hub, agent registration, or deployment is changed by this workflow.
