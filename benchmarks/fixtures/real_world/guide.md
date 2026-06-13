# Writing Your First Plugin

This guide walks through building a plugin from an empty file to a tested,
documented extension. By the end you will understand the plugin lifecycle, how
configuration flows in, and where to put your tests.

## Prerequisites

Before you start, make sure you have a working development environment:

1. A supported Python version installed.
2. The project cloned and installed in editable mode.
3. The test suite passing on a clean checkout.

If step 3 fails, stop and fix that first — a green baseline makes it much easier
to tell whether *your* change broke something.

## The plugin lifecycle

Every plugin moves through three phases. Understanding them is most of the
battle:

- **Registration.** The framework discovers your plugin and records its name,
  version, and the hooks it wants to participate in. Nothing runs yet.
- **Configuration.** User settings are resolved and frozen. Your plugin receives
  an immutable view of the relevant slice — it cannot mutate global state here.
- **Execution.** For each unit of work, the framework calls your hooks in
  dependency order. Hooks must be pure with respect to shared state.

A common mistake is to do real work during registration. Don't: registration
runs for *every* installed plugin, even ones the user never enables.

## A minimal plugin

```python
from framework import Plugin, hook

class Reverse(Plugin):
    name = "reverse"

    @hook("transform")
    def reverse_text(self, text: str) -> str:
        return text[::-1]
```

That's a complete, working plugin. Register it and every `transform` hook will
reverse the text passing through.

### Adding configuration

Configuration is declared, not parsed by hand:

```python
class Reverse(Plugin):
    name = "reverse"
    options = {"enabled": bool, "max_length": int}

    @hook("transform")
    def reverse_text(self, text: str) -> str:
        if not self.options["enabled"]:
            return text
        return text[: self.options["max_length"]][::-1]
```

> **Warning**
> Reading `self.options` outside a hook (for example, in `__init__`) raises
> `LifecycleError`, because configuration is not resolved until after
> registration completes.

## Testing

Treat plugins like any other unit. The framework ships a `harness` fixture that
gives you an isolated registry:

```python
def test_reverse(harness):
    harness.enable("reverse", max_length=3)
    assert harness.transform("hello") == "leh"
```

Run your tests in isolation first, then as part of the full suite — ordering
bugs only show up when other plugins are loaded alongside yours.

## Where to go next

- Read the [hook reference](hooks.md) for the full list of extension points.
- Browse the [examples directory](../examples) for end-to-end plugins.
- When you're ready to publish, follow the [packaging checklist](packaging.md).
