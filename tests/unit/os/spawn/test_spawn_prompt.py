from space.os import spawn


def test_spawn_prompt(tmp_path):
    result = spawn.spawn_prompt("test-agent", model="test-model")

    assert "You are test-agent." in result
    assert "Your model is test-model." in result
    assert "COMMAND REFERENCE" in result
    assert "memory --as test-agent" in result


def test_spawn_prompt_no_model(tmp_path):
    result = spawn.spawn_prompt("test-agent")

    assert "You are test-agent." in result
    assert "COMMAND REFERENCE" in result
    assert "memory --as test-agent" in result
    assert "Your model is" not in result


def test_spawn_prompt_format(tmp_path):
    result = spawn.spawn_prompt("sentinel")

    result.split("\n")
    assert "SPACE-OS MANUAL" in result
    assert "You are sentinel." in result
    assert "COMMAND REFERENCE" in result
