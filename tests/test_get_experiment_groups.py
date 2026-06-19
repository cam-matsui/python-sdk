import json
import os
import unittest
from unittest.mock import patch

from network_stub import NetworkStub
from statsig import statsig, StatsigOptions, StatsigServer

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../testdata/download_config_specs.json')) as r:
    CONFIG_SPECS_RESPONSE = r.read()

_api_override = "http://get-experiment-groups-test"
_network_stub = NetworkStub(_api_override)

_options = StatsigOptions(api=_api_override, disable_diagnostics=True)


def _make_specs_with_active_experiment():
    """
    Return a copy of the base config specs with sample_experiment patched to
    reflect what production specs look like:
      - isActive: True
      - experiment group rules have isExperimentGroup: True
      - the sizing/allocation rule (empty id) does NOT have isExperimentGroup set
    """
    specs = json.loads(CONFIG_SPECS_RESPONSE)
    for config in specs["dynamic_configs"]:
        if config["name"] == "sample_experiment":
            config["isActive"] = True
            for rule in config["rules"]:
                # Real group rules have a non-empty id and isExperimentGroup: True
                if rule.get("id"):
                    rule["isExperimentGroup"] = True
            break
    return specs


def _setup_network_stub(specs=None):
    _network_stub.reset()
    _network_stub.stub_request_with_value(
        "download_config_specs/.*", 200,
        specs if specs is not None else json.loads(CONFIG_SPECS_RESPONSE)
    )
    _network_stub.stub_request_with_value("log_event", 202, {})


@patch('requests.Session.request', side_effect=_network_stub.mock)
class TestGetExperimentGroupsOnServer(unittest.TestCase):
    """Tests for StatsigServer.get_experiment_groups"""

    @patch('requests.Session.request', side_effect=_network_stub.mock)
    def setUp(self, mock_request):
        _setup_network_stub(_make_specs_with_active_experiment())
        self._server = StatsigServer()
        self._server.initialize("secret-key", _options)

    def tearDown(self):
        self._server.shutdown()

    def test_returns_groups_for_known_experiment(self, mock_request):
        groups = self._server.get_experiment_groups("sample_experiment")

        self.assertIsInstance(groups, list)
        self.assertGreater(len(groups), 0)

    def test_group_shape_has_group_name_and_return_value(self, mock_request):
        groups = self._server.get_experiment_groups("sample_experiment")

        for group in groups:
            self.assertIn("group_name", group)
            self.assertIn("return_value", group)

    def test_group_names_match_spec(self, mock_request):
        groups = self._server.get_experiment_groups("sample_experiment")

        group_names = [g["group_name"] for g in groups]
        # Exactly the two variant groups — sizing rule must not appear
        self.assertEqual(sorted(group_names), ["Control", "Test"])

    def test_return_values_match_spec(self, mock_request):
        groups = self._server.get_experiment_groups("sample_experiment")

        groups_by_name = {g["group_name"]: g["return_value"] for g in groups}

        self.assertEqual(
            groups_by_name["Control"],
            {"experiment_param": "control", "layer_param": True, "second_layer_param": False},
        )
        self.assertEqual(
            groups_by_name["Test"],
            {"experiment_param": "test", "layer_param": True, "second_layer_param": True},
        )

    def test_returns_empty_list_for_unknown_experiment(self, mock_request):
        groups = self._server.get_experiment_groups("nonexistent_experiment")

        self.assertEqual(groups, [])

    def test_returns_empty_list_for_dynamic_config(self, mock_request):
        # dynamic configs are not experiments; should return []
        groups = self._server.get_experiment_groups("test_config")

        self.assertEqual(groups, [])

    def test_returns_empty_list_for_empty_name(self, mock_request):
        groups = self._server.get_experiment_groups("")

        self.assertEqual(groups, [])

    def test_filters_out_sizing_rule_without_is_experiment_group(self, mock_request):
        # The experimentSize/allocation rule has no isExperimentGroup field (absent = False).
        # It must not appear in the returned groups.
        groups = self._server.get_experiment_groups("sample_experiment")
        group_names = [g["group_name"] for g in groups]

        self.assertNotIn("experimentSize", group_names)

    def test_returns_empty_list_for_inactive_experiment(self, mock_request):
        # An experiment with isActive=False (or absent) should return []
        specs = _make_specs_with_active_experiment()
        for config in specs["dynamic_configs"]:
            if config["name"] == "sample_experiment":
                config["isActive"] = False
                break

        _network_stub.reset()
        _network_stub.stub_request_with_value("download_config_specs/.*", 200, specs)
        _network_stub.stub_request_with_value("log_event", 202, {})

        server = StatsigServer()
        server.initialize("secret-key", _options)

        groups = server.get_experiment_groups("sample_experiment")
        self.assertEqual(groups, [])

        server.shutdown()


@patch('requests.Session.request', side_effect=_network_stub.mock)
class TestGetExperimentGroupsModuleLevel(unittest.TestCase):
    """Tests for the module-level statsig.get_experiment_groups"""

    @classmethod
    @patch('requests.Session.request', side_effect=_network_stub.mock)
    def setUpClass(cls, mock_request):
        _setup_network_stub(_make_specs_with_active_experiment())
        statsig.initialize("secret-key", _options)

    @classmethod
    def tearDownClass(cls):
        statsig.shutdown()

    def test_module_level_returns_groups(self, mock_request):
        groups = statsig.get_experiment_groups("sample_experiment")

        self.assertIsInstance(groups, list)
        self.assertGreater(len(groups), 0)

    def test_module_level_group_shape(self, mock_request):
        groups = statsig.get_experiment_groups("sample_experiment")

        for group in groups:
            self.assertIn("group_name", group)
            self.assertIn("return_value", group)

    def test_module_level_returns_empty_for_unknown(self, mock_request):
        groups = statsig.get_experiment_groups("nonexistent_experiment")

        self.assertEqual(groups, [])


if __name__ == '__main__':
    unittest.main()
