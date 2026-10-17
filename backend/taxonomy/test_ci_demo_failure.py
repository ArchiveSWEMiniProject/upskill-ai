# Deliberately failing test: demonstrates that a red build blocks merging (UA-3).
# This branch is never merged.


def test_deliberate_failure_blocks_merge():
    assert 1 + 1 == 3
