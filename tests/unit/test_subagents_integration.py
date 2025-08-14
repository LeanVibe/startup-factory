from tools.dev.subagents import tester, editor, verifier


def test_subagents_have_minimal_interfaces():
    assert hasattr(tester, "run") and callable(tester.run)
    assert hasattr(editor, "run") and callable(editor.run)
    assert hasattr(verifier, "run") and callable(verifier.run)
