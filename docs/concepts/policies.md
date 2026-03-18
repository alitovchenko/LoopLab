# Policies

**Role:** Map **model output** → **`ControlSignal`**: an `action` string, `params` dict, and **validity window** in LSL time. Only signals the task actually applies should drive adaptation logs you care about.

- Registered by name (`policy` in config).
- May return no-op or skip emitting signals under some conditions.

**Config:** `policy` + `policy_config` (e.g. `validity_seconds`).

**Adaptation target** in run reports is often derived from policy name + first logged control action, or from `session_summary.paradigm` for tagged demos.

See: [Add a policy](../extensions/add_policy.md), [Task adapters](task_adapters.md).
