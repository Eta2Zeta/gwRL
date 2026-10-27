"""Recomputed parallel grammar validation for a subtree replacement forest.

This is an execution helper, not a trusted-producer certificate. The original
editor still decides when replacement validity is relevant, and retains every
source/target/size/type/arity/capacity/section/cohort check and error bit.
"""
from dataclasses import replace

import torch

from .device_tree_validation import validate_source


def validate_replacement(state, blocks, block_lengths, selected):
    """Check all actual selected replacement nodes with the original pools.

    The temporary complete buffer frame borrows source context/string pools and
    section-shape metadata. Sections are unused by generic tree grammar. A
    replacement has no inherited source error; the editor checks those source
    errors separately in their original order. No host values, cache or fallback.
    """
    frame = replace(state, records=blocks, lengths=block_lengths,
                    errors=torch.zeros_like(state.errors))
    return validate_source(frame, selected)
