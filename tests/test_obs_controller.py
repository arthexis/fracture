from obs_plugins.layout import DEFAULT_LAYOUT
from obs_plugins.obs_controller import OBSController


class _Resp:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeWS:
    def __init__(self):
        self.scenes = []
        self.inputs = []
        self.items = []
        self.calls = []

    def get_scene_list(self):
        return _Resp(scenes=[{"sceneName": s} for s in self.scenes])

    def create_scene(self, name):
        self.scenes.append(name)

    def get_input_list(self):
        return _Resp(inputs=[{"inputName": n} for n in self.inputs])

    def create_input(self, scene, name, kind, settings, enabled):
        self.inputs.append(name)
        self.calls.append(("create_input", name, kind))

    def set_input_settings(self, name, settings, overlay):
        self.calls.append(("set_input", name, settings))

    def get_scene_item_list(self, _scene):
        return _Resp(scene_items=self.items)

    def create_scene_item(self, _scene, source_name):
        item_id = len(self.items) + 1
        self.items.append({"sourceName": source_name, "sceneItemId": item_id})
        return _Resp(scene_item_id=item_id)

    def set_scene_item_transform(self, scene, item_id, transform):
        self.calls.append(("transform", scene, item_id, transform))

    def set_scene_item_enabled(self, scene, item_id, enabled):
        self.calls.append(("enabled", scene, item_id, enabled))


def test_ensure_layout_creates_scene_and_sources():
    ws = FakeWS()
    c = OBSController(ws)
    c.ensure_layout("https://chat", "hello", "/tmp/a.png", "/tmp/b.png")
    assert "LiveLayout_Main" in ws.scenes
    assert "Chat_Widget" in ws.inputs
    assert "SpeakerCard_Art" in ws.inputs
    assert any(call[0] == "transform" for call in ws.calls)


def test_layout_geometry_matches_expected():
    assert DEFAULT_LAYOUT.chat_rect.height == 660
    assert DEFAULT_LAYOUT.speaker_rect.y == 660
    assert DEFAULT_LAYOUT.notes_rect.height == 120


def test_set_speaker_mode_hybrid_toggles_items():
    ws = FakeWS()
    c = OBSController(ws)
    c.ensure_layout("https://chat", "hello", "/tmp/a.png", "/tmp/b.png")
    ws.create_input("LiveLayout_Main", "SpeakerCard_Camera", "monitor_capture", {}, True)
    ws.create_scene_item("LiveLayout_Main", "SpeakerCard_Camera")
    c.set_speaker_mode("hybrid")
    enabled_calls = [call for call in ws.calls if call[0] == "enabled"]
    assert enabled_calls
