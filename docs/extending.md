# Extending DockRx

There is **no CLI scaffold** yet (`dockrx rule new` is not implemented).
You create rules by adding files under `.dockrx/`; `dockrx analyze` loads them automatically.

DockRx loads local rules and plugins from:

```text
.dockrx/
  rules/*.yaml
  plugins/*.py
```

Load order:

1. built-in YAML rules
2. built-in Python plugins
3. `.dockrx/rules/*.yaml`
4. `.dockrx/plugins/*.py`

If the same rule ID appears more than once, the later source wins.

## Create Your First Rule

### YAML rule

Add `.dockrx/rules/DRX900_my_check.yaml`:

```yaml
id: DRX900
title: Disallow curl | bash installs
severity: HIGH
category: security
tags: [supply-chain]
applies_to: [dockerfile]
pack: project@local

detect:
  all:
    - instruction: RUN
      args_match: "curl .*\\|\\s*b?ash"

recommendation: |
  Avoid piping remote scripts into a shell.
  Vendor install scripts or use distro packages.

estimated_saving:
  confidence: heuristic

references:
  - https://docs.docker.com/build/building/best-practices/
```

Then verify:

```bash
dockrx analyze .
dockrx explain DRX900 --path .
```

The detect DSL supports:

- `all` / `any` / `not`
- `instruction`
- `args_match` (regex)
- `stage` (`final` | `any` | explicit stage name)
- `before` / `after` (same-stage by default)
- `missing: true`

### Python plugin

Add `.dockrx/plugins/my_check.py`:

```python
from dockrx.context import AnalysisContext
from dockrx.models import Finding
from dockrx.plugins.base import finding_from_meta

RULE = {
    "id": "DRX901",
    "title": "Custom company check",
    "severity": "MEDIUM",
    "category": "best_practices",
    "applies_to": ["dockerfile", "project"],
    "recommendation": "Fix the custom issue.",
    "pack": "project@local",
}

def check(ctx: AnalysisContext) -> list[Finding]:
    # inspect ctx.graph, ctx.has_dockerignore, etc.
    # return [finding_from_meta(RULE, line=..., stage=...)] when matched
    return []
```

Built-in rules live in `src/dockrx/rules/builtin/` (YAML) and `src/dockrx/plugins/` (Python).
Today that is roughly **27 rule IDs** across both.
