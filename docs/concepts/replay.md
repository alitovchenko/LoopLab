# Replay

**Role:** Prove **determinism** of the online pipeline: re-feed **recorded stream chunks** in order, re-run preprocess → features → model → policy, and compare emitted control signals to those stored in **events.jsonl**.

- **`replay_result.json`:** match counts, optional divergences list.
- **`proof-run`** runs replay automatically after the session.
- **Strict mode:** `proof-run --strict` or `replay --strict` exits non-zero on mismatch.

Run reports surface **replay_agreement** (matches, counts, sample divergences) for methods text.

See: [Quickstart](../quickstart.md), stress replay under `examples/stress_replay/`.
