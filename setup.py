from __future__ import annotations

from pathlib import Path

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup


ROOT = Path(__file__).resolve().parent


ext_modules = [
    Pybind11Extension(
        "gwrl_cpp",
        [
            "src/campaign_benchmarks.cpp",
            "src/campaign_audit.cpp",
            "src/campaign_actions.cpp",
            "src/campaign_env.cpp",
            "src/campaign_objective.cpp",
            "src/campaign_runtime.cpp",
            "src/campaign_setup.cpp",
            "src/campaign_state.cpp",
            "src/catalog.cpp",
            "src/movement.cpp",
            "src/economy.cpp",
            "src/income_batch.cpp",
            "src/device_state.cpp",
            "src/income_ledger_batch.cpp",
            "src/wealth_context.cpp",
            "src/relations_context.cpp",
            "src/movement_context.cpp",
            "src/catalog_stats_context.cpp",
            "src/recruitment_context.cpp",
            "src/economy_lendlease.cpp",
            "src/land_combat.cpp",
            "src/air.cpp",
            "src/naval.cpp",
            "src/naval_movement.cpp",
            "src/naval_combat.cpp",
            "src/naval_operations.cpp",
            "src/neural_graph.cpp",
            "src/numeric_graph.cpp",
            "src/politics.cpp",
            "src/politics_influence.cpp",
            "src/politics_warlords.cpp",
            "src/japan_training_env.cpp",
            "src/python_bindings.cpp",
            "src/simple_json.cpp",
        ],
        define_macros=[("GWRL_SOURCE_DIR", chr(34) + str(ROOT) + chr(34))],
        include_dirs=[str(ROOT / "include")],
        depends=[str(path.relative_to(ROOT)) for path in
                 sorted((ROOT / "include").rglob("*.hpp")) + sorted((ROOT / "src").rglob("*.inc"))],
        cxx_std=20,
        extra_compile_args=["-mmacosx-version-min=13.3"],
        extra_link_args=["-mmacosx-version-min=13.3"],
    )
]


setup(
    name="gwrl_cpp",
    version="0.1.0",
    description="C++ training environment bindings for gwRL",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
