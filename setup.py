from __future__ import annotations

from pathlib import Path

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup


ROOT = Path(__file__).resolve().parent


ext_modules = [
    Pybind11Extension(
        "gwrl_cpp",
        [
            "src/action_encoder.cpp",
            "src/game_state.cpp",
            "src/japan_training_env.cpp",
            "src/python_bindings.cpp",
            "src/setup_loader.cpp",
            "src/simple_json.cpp",
            "src/state_encoder.cpp",
        ],
        include_dirs=[str(ROOT / "include")],
        cxx_std=20,
        extra_compile_args=["-mmacosx-version-min=10.15"],
        extra_link_args=["-mmacosx-version-min=10.15"],
    )
]


setup(
    name="gwrl_cpp",
    version="0.1.0",
    description="C++ training environment bindings for gwRL",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
