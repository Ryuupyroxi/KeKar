import importlib


def test_main_module_imports():
    import src.main as main_module
    assert callable(main_module.main)


def test_app_module_imports():
    import src.app as app_module
    assert hasattr(app_module, "Application")


def test_all_core_modules_import():
    for name in ("src.paths", "src.config.settings", "src.config.crypto",
                 "src.data.db", "src.data.property_repo",
                 "src.data.applicant_repo", "src.data.backup",
                 "src.data.chat_repo", "src.services.listing_compiler",
                 "src.services.clipboard", "src.services.image_service",
                 "src.agent.soul", "src.agent.memory", "src.agent.client",
                 "src.agent.tools", "src.agent.runner"):
        importlib.import_module(name)
