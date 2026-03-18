# Experiment state

**Role (optional):** Describe adaptation in **trial / block** language, not only as raw control signals.

LoopLab provides types such as **`ExperimentState`**, **`TrialContext`**, **`BlockContext`**, **`TrialOutcome`**. Your task:

- Updates adaptive parameters when applying control signals (e.g. difficulty, stimulus size).
- Calls the event logger for `trial_start`, `block_start`, `trial_outcome`, `adaptive_params_update`, etc.

The runner does **not** create experiment state for you—demos that need it construct state in the task script and pass it where needed.

**Run reports:** Event counts appear under experiment summary; PsychoPy e2e runs add a **task-level summary** when `paradigm: psychopy_e2e` is set.

See: [Tutorial: PsychoPy e2e](../tutorials/psychopy_e2e.md), main README “Experiment abstraction”.
