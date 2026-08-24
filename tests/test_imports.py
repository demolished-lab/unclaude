def test_imports():
    import rig
    import rig.cli
    import rig.schema
    assert rig.__version__.startswith("0.1.0")
