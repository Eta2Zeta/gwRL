from __future__ import annotations

from pathlib import Path
import sys

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup


ROOT = Path(__file__).resolve().parent
# Two separate lists: Pybind11Extension adds its own compile flags to the one
# and link flags to the other in place, so one shared list would pass each set
# to both the compiler and the linker.
if sys.platform == "darwin":
    COMPILE_ARGS, LINK_ARGS = ["-mmacosx-version-min=13.3"], ["-mmacosx-version-min=13.3"]
elif sys.platform == "win32":
    # MSVC otherwise reads the UTF-8 sources in the system code page, which
    # changes the bytes of non-ASCII names in string literals.
    COMPILE_ARGS, LINK_ARGS = ["/utf-8"], []
else:
    COMPILE_ARGS, LINK_ARGS = [], []


ext_modules = [
    Pybind11Extension(
        "gwrl_cpp",
        [
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
            "src/economy_lendlease.cpp",
            "src/land_combat.cpp",
            "src/air.cpp",
            "src/naval.cpp",
            "src/naval_movement.cpp",
            "src/naval_combat.cpp",
            "src/naval_operations.cpp",
            "src/politics.cpp",
            "src/politics_influence.cpp",
            "src/politics_warlords.cpp",
            "src/inference_client.cpp",
            "src/python_bindings.cpp",
            "src/python_random.cpp",
            "src/search.cpp",
            "src/simple_json.cpp",
            "src/zone_encoding.cpp",
        ],
        # Forward slashes: a Windows path's backslashes would be escapes in a C string.
        define_macros=[("GWRL_SOURCE_DIR", chr(34) + ROOT.as_posix() + chr(34))],
        include_dirs=[str(ROOT / "include")],
        cxx_std=20,
        extra_compile_args=COMPILE_ARGS,
        extra_link_args=LINK_ARGS,
    )
]


setup(
    name="gwrl_cpp",
    version="0.1.0",
    description="C++ training environment bindings for gwRL",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
