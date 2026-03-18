# Add a policy

1. Implement **`Policy`**: consume model output + context, return **`ControlSignal`** (or None / no-op when appropriate).
2. **`register_policy("my_policy", MyPolicy, default_config_dict)`**.
3. Config:

   ```yaml
   policy: "my_policy"
   policy_config:
     validity_seconds: 1.0
   ```

4. Run **`validate-config`**; run a short proof-run or demo and check **`run_report.md`** for adaptation counts and first control action.

See `src/looplab/controller/policy.py`, [Concepts: Policies](../concepts/policies.md).
