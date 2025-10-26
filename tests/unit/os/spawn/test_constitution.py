from space.os import spawn


def test_identity_prompt(tmp_path):
    result = spawn.build_identity_prompt("test-agent", model="test-model")

    assert "You are test-agent." in result
    assert "Your model is test-model." in result
    assert "space commands:" in result
    assert "`space`" in result
    assert "`memory --as test-agent`" in result


def test_identity_prompt_no_model(tmp_path):
    result = spawn.build_identity_prompt("test-agent")

    assert "You are test-agent." in result
    assert "space commands:" in result
    assert "`memory --as test-agent`" in result
    assert "Your model is" not in result


def test_identity_prompt_format(tmp_path):
    result = spawn.build_identity_prompt("sentinel")

    lines = result.split("\n")
    assert lines[0] == "You are sentinel."
    assert "space commands:" in result
