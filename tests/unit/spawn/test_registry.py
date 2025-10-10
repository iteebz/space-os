from space.spawn import registry, spawn


def test_save_and_get_agent_identity(in_memory_db):
    full_identity = "You are a test agent.\nSelf: I am a test.\n\nConstitution: Test."
    constitution_hash = spawn.hash_content(full_identity)

    registry.save_constitution(constitution_hash, full_identity)
    retrieved_identity = registry.get_constitution(constitution_hash)
    assert retrieved_identity == full_identity

    updated_full_identity = (
        "You are an updated test agent.\nSelf: I am updated.\n\nConstitution: Updated Test."
    )
    updated_constitution_hash = spawn.hash_content(updated_full_identity)
    registry.save_constitution(updated_constitution_hash, updated_full_identity)
    retrieved_updated_identity = registry.get_constitution(updated_constitution_hash)
    assert retrieved_updated_identity == updated_full_identity

    non_existent_identity = registry.get_constitution("nonexistenthash")
    assert non_existent_identity is None


def test_save_long_identity(test_space):
    long_full_identity = "A" * 10000
    constitution_hash = spawn.hash_content(long_full_identity)

    registry.save_constitution(constitution_hash, long_full_identity)
    retrieved_identity = registry.get_constitution(constitution_hash)
    assert retrieved_identity == long_full_identity


def test_save_special_chars_identity(test_space):
    special_char_identity = "Hello!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
    constitution_hash = spawn.hash_content(special_char_identity)

    registry.save_constitution(constitution_hash, special_char_identity)
    retrieved_identity = registry.get_constitution(constitution_hash)
    assert retrieved_identity == special_char_identity
