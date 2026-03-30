"""Plugin stub rendering from bundled templates."""

from looplab.plugin_stub import minimal_config_yaml_for_plugin, render_plugin_stub


def test_render_plugin_stub_model():
    s = render_plugin_stub("model", "my_alpha")
    assert "class MyAlpha" in s
    assert "register_model(" in s and "my_alpha" in s
    assert "MyModel" not in s


def test_minimal_config_yaml():
    y = minimal_config_yaml_for_plugin("xfeat", "feature")
    assert "feature_extractor: \"xfeat\"" in y
    assert "validate-config" in y
