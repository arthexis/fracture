from obs_plugins.presets import PRESETS


def test_presets_include_expected_states():
    for key in ["prep", "live", "discussion", "brb"]:
        assert key in PRESETS
