# Public metadata demonstration — September 28, 2026

The [JSON report](sample-report.json) was produced by `python make_sample.py` from a synthetic workflow containing three public action references. Four metadata documents were actually retrieved. SHA-256 hashes and the observation timestamp are in the report. No workflow or action was executed.

| Workflow reference | Observed declaration | Interpretation |
| --- | --- | --- |
| `actions/checkout@v4` | `node20` | Review this pinned major's release notes and replacement; not proof of failure. |
| `actions/checkout@v5` | `node24` | Runtime declaration matches; behavior still requires testing. |
| `anthropics/claude-code-action@v1.0.52` | `composite` | Follow its nested action references. |
| Nested `oven-sh/setup-bun@3d267786b128fe76c2f16a390aa2448b815359f3` | `node20` | The full chain appears in the report, even though the outer action is composite. |

Two runtime declarations warrant review; zero unresolved references in this deliberately narrow fixture. No statement is made about current default branches, all releases of these actions, a customer's repository, or actual CI failure. These historical pins were chosen to exercise the tool; their presence is not evidence of current customer demand.

The eight automated tests cover nested composites, immutable reference handling, reusable workflows, cycles, offline behavior, dynamic references, path containment, malformed YAML, caching/read bounds, and avoiding false positives from comments, scripts and application Node settings.

The tool does not choose a replacement pin automatically. A paid migration includes checking actual release differences and preserving intentional security pins; simply replacing all version numbers would be inadequate.
