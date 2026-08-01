from spread_research.reporting import config_hash, log_experiment, next_experiment_id


def test_config_hash_stable_and_order_independent():
    assert config_hash({"a": 1, "b": 2}) == config_hash({"b": 2, "a": 1})
    assert config_hash({"a": 1}) != config_hash({"a": 2})


def test_experiment_log_roundtrip(tmp_path):
    log = tmp_path / "exp.csv"
    eid1 = log_experiment(data_period="2020-2024", pairs="MES_MNQ",
                          model_type="zscore", parameters={"entry_z": 2.0},
                          cost_scenario="stressed", result_summary="test",
                          log_path=log)
    eid2 = log_experiment(data_period="2020-2024", pairs="ZT_ZN",
                          model_type="zscore", parameters={"entry_z": 2.5},
                          cost_scenario="stressed", result_summary="test2",
                          log_path=log)
    assert eid1 == "EXP-001" and eid2 == "EXP-002"
    assert next_experiment_id(log) == "EXP-003"
    text = log.read_text()
    assert "MES_MNQ" in text and "ZT_ZN" in text
