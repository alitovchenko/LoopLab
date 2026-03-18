# Models

**Role:** Map **features** → **model output** (e.g. vector, dict with confidence, latent variables). The model should be **deterministic given fixed seed** where randomness is used, so replay can match.

- Registered by name (`model` in config).
- `identity` passes features through; custom models implement the `Model` protocol.

**Config:** `model` + `model_config`.

**Events:** Model outputs can be logged for debugging/analysis depending on logger settings.

See: [Add a model](../extensions/add_model.md), `list-components --models`.
