import subprocess


def test_check_shows_agent_dashboard():
    result = subprocess.run(
        ["space", "check", "zealot-2"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    assert "Agent: zealot-2" in result.stdout
    assert "Spawns:" in result.stdout
    assert "Messages:" in result.stdout
    assert "Knowledge:" in result.stdout


def test_check_nonexistent_agent():
    result = subprocess.run(
        ["space", "check", "nonexistent"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 1
    assert "not found" in result.stdout
