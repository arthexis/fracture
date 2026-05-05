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
        self.filters = {}

    def get_scene_list(self):
        return _Resp(scenes=[{"sceneName": s} for s in self.scenes])

    def create_scene(self, name):
        self.scenes.append(name)

    def get_input_list(self):
        return _Resp(inputs=[{"inputName": n} for n in self.inputs])

    def get_input_kind_list(self, _unversioned):
        return _Resp(input_kinds=[
            {"inputKind": "monitor_capture"},
            {"inputKind": "browser_source"},
            {"inputKind": "image_source"},
            {"inputKind": "color_source_v3"},
            {"inputKind": "text_ft2_source_v2"},
        ])

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

    def get_source_filter_list(self, source_name):
        return _Resp(filters=self.filters.get(source_name, []))

    def create_source_filter(self, source_name, filter_name, filter_kind, settings):
        self.filters.setdefault(source_name, []).append({"filterName": filter_name, "filterKind": filter_kind, "settings": settings})
        self.calls.append(("create_filter", source_name, filter_name))

    def set_source_filter_settings(self, source_name, filter_name, settings, overlay):
        self.calls.append(("set_filter", source_name, filter_name, settings))

    def remove_source_filter(self, source_name, filter_name):
        self.filters[source_name] = [f for f in self.filters.get(source_name, []) if f["filterName"] != filter_name]
        self.calls.append(("remove_filter", source_name, filter_name))



def test_ensure_layout_creates_scene_and_sources():
    ws = FakeWS()
    c = OBSController(ws)
    report = c.ensure_layout("https://chat", "hello", "/tmp/a.png", "/tmp/b.png")
    assert "LiveLayout_Main" in ws.scenes
    assert "Chat_Widget" in ws.inputs
    assert "SpeakerCard_Art" in ws.inputs
    assert any(call[0] == "transform" for call in ws.calls)
    assert report["created"]


def test_layout_geometry_matches_expected():
    assert DEFAULT_LAYOUT.chat_rect.height == 660
    assert DEFAULT_LAYOUT.speaker_rect.y == 660
    assert DEFAULT_LAYOUT.notes_rect.height == 120


def test_set_speaker_mode_hybrid_toggles_items():
    ws = FakeWS()
    c = OBSController(ws)
    report = c.ensure_layout("https://chat", "hello", "/tmp/a.png", "/tmp/b.png")
    ws.create_input("LiveLayout_Main", "SpeakerCard_Camera", "monitor_capture", {}, True)
    ws.create_scene_item("LiveLayout_Main", "SpeakerCard_Camera")
    c.set_speaker_mode("hybrid")
    enabled_calls = [call for call in ws.calls if call[0] == "enabled"]
    assert enabled_calls


def test_apply_preset_live_sets_visibility_calls():
    ws = FakeWS()
    c = OBSController(ws)
    report = c.ensure_layout("https://chat", "hello", "/tmp/a.png", "/tmp/b.png")
    ws.create_input("LiveLayout_Main", "SpeakerCard_Camera", "monitor_capture", {}, True)
    ws.create_scene_item("LiveLayout_Main", "SpeakerCard_Camera")
    c.apply_preset("live")
    enabled_calls = [call for call in ws.calls if call[0] == "enabled"]
    assert len(enabled_calls) >= 3


def test_probe_capabilities_reports_supported_kinds():
    ws = FakeWS()
    c = OBSController(ws)
    caps = c.probe_capabilities()
    assert caps["browser_source_supported"] is True
    assert caps["text_source_supported"] is True


def test_camera_filter_preset_upserts_and_removes_filter():
    ws = FakeWS()
    c = OBSController(ws)
    c.ensure_layout("https://chat", "hello", "/tmp/a.png", "/tmp/b.png")
    ws.create_input("LiveLayout_Main", "SpeakerCard_Camera", "dshow_input", {}, True)
    ws.create_scene_item("LiveLayout_Main", "SpeakerCard_Camera")
    c.set_camera_filter_preset("cinematic")
    assert any(call[0] == "create_filter" for call in ws.calls)
    c.set_camera_filter_preset("none")
    assert any(call[0] == "remove_filter" for call in ws.calls)


def test_set_camera_crop_updates_transform():
    ws = FakeWS()
    c = OBSController(ws)
    c.ensure_layout("https://chat", "hello", "/tmp/a.png", "/tmp/b.png")
    ws.create_input("LiveLayout_Main", "SpeakerCard_Camera", "dshow_input", {}, True)
    ws.create_scene_item("LiveLayout_Main", "SpeakerCard_Camera")
    c.set_camera_crop(10, 20, 30, 40)
    transform_calls = [call for call in ws.calls if call[0] == "transform"]
    assert transform_calls


def test_snapshot_restore_and_locking():
    ws = FakeWS()
    c = OBSController(ws)
    snap = c.snapshot_state()
    c.set_share_source("AnotherShare")
    assert c.names.share == "AnotherShare"
    c.restore_state(snap)
    assert c.names.share == "Main_Share_Capture"
    c.lock_layout()
    assert c.is_layout_locked() is True
