"""Policy: model output -> control signal; registry for plug-in policies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Type

from looplab.controller.signals import ControlSignal, ModelOutput
from looplab.exceptions import UnknownComponentError
from looplab.streams.clock import lsl_clock

# Registry: name -> (class or factory, default config, meta)
_POLICY_REGISTRY: dict[str, tuple[Type["Policy"] | Callable[..., "Policy"], dict[str, Any], dict[str, Any]]] = {}


def _unpack_policy_entry(entry: tuple) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    if len(entry) == 2:
        return entry[0], entry[1], {}
    return entry[0], entry[1], entry[2]


class Policy(ABC):
    """Given model output and context, produce a control signal."""

    @abstractmethod
    def __call__(
        self,
        model_output: ModelOutput,
        context: dict[str, Any],
    ) -> ControlSignal:
        ...


def get_policy_registry() -> dict[str, tuple[Type[Policy] | Callable[..., Policy], dict[str, Any], dict[str, Any]]]:
    return _POLICY_REGISTRY.copy()


def register_policy(
    name: str,
    policy_class: Type[Policy] | Callable[..., Policy],
    default_config: dict[str, Any] | None = None,
    *,
    component_version: str | None = None,
) -> None:
    """Register a policy by name for config-based lookup."""
    meta: dict[str, Any] = {}
    if component_version:
        meta["version"] = component_version
    _POLICY_REGISTRY[name] = (policy_class, default_config or {}, meta)


def create_policy(name: str, config: dict[str, Any] | None = None) -> Policy:
    """Instantiate a registered policy by name with optional config overrides."""
    if name not in _POLICY_REGISTRY:
        raise UnknownComponentError("policy", name, list(_POLICY_REGISTRY))
    policy_class, defaults, _meta = _unpack_policy_entry(_POLICY_REGISTRY[name])
    opts = {**defaults, **(config or {})}
    if isinstance(policy_class, type):
        return policy_class(**opts)
    return policy_class(**opts)


class IdentityPolicy(Policy):
    """Map model output value 1:1 to control: action='set_value', params={'value': output.value}."""

    def __init__(self, validity_seconds: float = 1.0):
        self._validity_seconds = validity_seconds

    def __call__(
        self,
        model_output: ModelOutput,
        context: dict[str, Any],
    ) -> ControlSignal:
        now = lsl_clock()
        return ControlSignal(
            action="set_value",
            params={"value": model_output.value},
            valid_until_lsl_time=now + self._validity_seconds,
        )


register_policy("identity", IdentityPolicy, {"validity_seconds": 1.0}, component_version="1.0.0")
