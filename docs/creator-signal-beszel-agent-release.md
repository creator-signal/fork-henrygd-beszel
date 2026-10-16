# Creator Signal Beszel release

`creator-signal/main` is the standalone Creator Signal reconciliation branch for the upstream `henrygd/beszel` `v0.20.0` source line. Upstream remains pullable through the `upstream` remote; Creator Signal changes stay on `creator-signal/*` branches and are reconciled there before release.

**Creator Signal CI** is the sole downstream publication workflow. Dispatch it from `creator-signal/main` with a new unused immutable `v0.20.0-cs.N` tag. The image names below use the historical `v0.20.0-cs.1` example. It checks that the tag points to the selected source revision, publishes the GoReleaser binary packages to the GitHub release, and publishes these multi-platform images:

- `ghcr.io/creator-signal/fork-henrygd-beszel/beszel:v0.20.0-cs.1`
- `ghcr.io/creator-signal/fork-henrygd-beszel/beszel-agent:v0.20.0-cs.1` and `:v0.20.0-cs.1-alpine`
- `ghcr.io/creator-signal/fork-henrygd-beszel/beszel-agent-nvidia:v0.20.0-cs.1`
- `ghcr.io/creator-signal/fork-henrygd-beszel/beszel-agent-intel:v0.20.0-cs.1`

Each image also has an exact source-SHA tag and BuildKit SBOM/provenance attestations. The GitHub release contains the binary packages, checksums, and `creator-signal-release-manifest.json`, which records the upstream baseline, exact source revision, and immutable image digests. No host, Hub, agent registration, or deployment is changed by this workflow.

## Native signed agent release

Production host agents and VM guests do not consume the GoReleaser packages above. They consume a natively qualified, Ed25519-signed agent release attached to the same immutable GitHub release by the Forgejo job `Beszel Agent Linux amd64 qualification` (`.forgejo/workflows/beszel-agent-qualification.yml`).

1. Dispatch `Creator Signal CI` for `vX.Y.Z-cs.N` to create the release with its binary packages and images.
2. From `creator-signal/main`, dispatch the Forgejo qualification job with `source_revision` set to the exact release source commit and `release_tag` set to `vX.Y.Z-cs.N`.
3. The job rebuilds and tests the agent on the protected `native-linux-amd64` runner, emits the SPDX SBOM, assembles `creator-signal-beszel-agent-release.json` (`creator-signal.beszel-agent-release/v1`), signs it, asserts the observed public-key fingerprint, and uploads both assets to the GitHub release.

Required governed values, never committed:

| Name | Kind | Purpose |
| --- | --- | --- |
| `BESZEL_RELEASE_SIGNING_KEY` | Forgejo secret | Ed25519 PKCS#8 PEM private key used to sign the manifest. |
| `BESZEL_RELEASE_PUBLIC_KEY_SHA256` | Forgejo variable | SPKI DER SHA-256 of the matching public key, asserted against the produced signature. |
| `CREATOR_SIGNAL_RELEASE_TOKEN` | Forgejo secret | GitHub token with `contents: write` used to upload the two assets to the release. |

`creator-signal-beszel-agent-release.signature.json` carries `algorithm` (`Ed25519`), `publicKeySha256`, `manifestSha256`, the base64 `signature` and `sourceRevision`. Sales Pulse verifies the signature before rendering any host-agent manifest.

## Provider-only Hub sign-in

A Hub with password authentication disabled and one OAuth provider waits for the user to click the provider button. The click opens the popup synchronously through the existing guarded popup path, then starts the PocketBase OAuth flow. A blocked popup reports the existing error and leaves the button available for retry. Do not work around a disabled provider button by changing browser storage, enabling passwords, or changing `OAUTH_DISABLE_POPUP`: the latter changes the callback journey.

Run `bun run test:login` from `internal/site` for the mounted React regression tests. They cover the idle provider-only form, explicit-click popup and successful authentication, and blocked-popup retry with a synthetic SDK adapter. `bun test` also runs the existing frontend tests; `bun run build` builds the production Hub assets. These checks do not establish a real provider login or deployment acceptance.

Issue #23 fixes the automatic timer popup that can leave the OAuth SDK pending after popup blocking. Its next proposed immutable release is `v0.20.0-cs.3` (`cs.1` and `cs.2` already exist); recheck tag availability before publication. The upstream application version remains `0.20.0`, and the downstream `cs.N` tag identifies this repair. After independent review and merge into `creator-signal/main`, use the existing **Creator Signal CI** operation above. The parent release owner verifies its immutable artifacts before changing any Sales Pulse consumer selection; no deployment is implied by this source repair.
