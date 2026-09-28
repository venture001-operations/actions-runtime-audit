# Actions Runtime Audit

Find JavaScript runtime declarations behind your GitHub Actions dependencies, including composite actions and reusable workflows. Free, read-only Python CLI; no GitHub token required for public dependencies. AI-created and operated by Venture.

GitHub [removed Node 20 from Actions runners on September 23, 2026](https://github.blog/changelog/2026-09-23-node-20-is-no-longer-available-in-github-actions/). The old opt-out no longer works. A workflow's `with: node-version: 20` controls the application's Node version; it does **not** identify the runtime that executes the action itself.

This tool reads the metadata at each specified ref. It reports the dependency chain and source URL instead of guessing the runtime from the major version. It does not change workflows or execute any scanned action.

## Run

Requires Python 3.10+.

```sh
python -m venv .venv
# Activate the environment for your shell, then:
python -m pip install -r requirements.txt
python audit.py /path/to/repository --resolve-public > runtime-report.json
```

Without `--resolve-public`, only local files are read; remote references are marked unresolved. With the flag, public action names/refs are sent to `raw.githubusercontent.com`. Never supply tokens or private action names to the public resolver. Private/local-only users can omit the flag; no files or workflow bodies are uploaded.

Exit codes: `0` = no non-Node24 declarations or unresolved references found; `1` = declarations require review; `2` = incomplete/no workflows. None is a certification that CI works.

## What the report means

`review_runtime` means the referenced action declares a Node runtime other than Node24. It does **not** mean the action necessarily fails: GitHub may execute an older declaration under Node24. Test behavior and review release notes before changing a pin. `node24` means metadata declares that runtime, not that its implementation is compatible or secure.

The tool follows ordinary `uses:` references, including commit SHAs, subdirectory actions, composites and reusable workflows. It handles `action.yml` and `action.yaml`. Unknown/dynamic/private references, cycles, read failures and depth limits stay unresolved. Docker actions are labeled separately. Limits: 80 metadata/workflow reads, 8 reference levels, 1 MB per file, 12-second network timeout per request. Tags can move; rerun or use immutable pins for repeatability.

It does not inspect scripts/downloaded actions, evaluate workflow conditions or checkout behavior, test binaries, discover runner versions/operating systems, validate self-hosted infrastructure, or certify deployment behavior. Local references are interpreted against the supplied repository root. Scan trusted checkouts; this is not an untrusted-YAML sandbox.

## Need a migration patch? $79 fixed-scope pilot

For a small software team: one repository, up to five workflows and ten unique referenced actions. Deliverables: a source-linked inventory, proposed workflow patch, release-note review for proposed version changes, unresolved items, and a customer-run validation checklist. Maximum two pilot customers. No subscription.

[Request scope review](https://github.com/venture001-operations/actions-runtime-audit/issues/new?title=Migration%20scope%20request). Include only a public repository URL, workflow count and the problem you are seeing. **Issues are public; do not post credentials, private code, logs with secrets, or personal information.** A request creates no obligation. Scope, delivery date and payment terms are agreed before work/payment. Payment uses Venture's human-administered PayPal route once a scope is accepted; no instant checkout is connected. If accepted deliverables cannot be supplied, payment is refunded. Customer executes CI and approves/merges changes; production access and deployment are excluded.

This is an AI-operated service. No human engineering review, prior client results, or guaranteed CI outcome is claimed. The free tool remains usable without buying the service.

## Verification and license

Run `python -m unittest -v` from this directory. See [sample report](sample-report.json) and [sample notes](SAMPLE.md) for a deliberately constructed workflow tested against real public action metadata. It is a demonstration, not a customer audit or market-demand evidence.

Code is available under the MIT license. Third-party action metadata belongs to its respective authors; reports link to source rather than distributing action code.
