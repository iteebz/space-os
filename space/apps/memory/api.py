from .repo import MemoryRepo

# Instantiate the repository, which is a self-contained component.
repo = MemoryRepo()

def add_memory(identity: str, topic: str, message: str):
    """Adds a memory to the store."""
    repo.add(identity, topic, message)

def get_all_memories():
    """Retrieves all memories from the store."""
    return repo.get_all()
