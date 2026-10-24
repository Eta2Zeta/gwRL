#pragma once

#include <pybind11/pybind11.h>

namespace game::neural {

// Compile public JSON source features only. Python callbacks retain the exact
// established Unicode tokenization and numerical feature semantics; no engine
// state, learned tensors or random generator is read by this interface.
pybind11::dict compileCampaignGraph(
    pybind11::handle value,
    pybind11::object buckets,
    const pybind11::function& lexicalIds,
    const pybind11::function& stringDescriptor,
    const pybind11::function& numericFeatures);

}  // namespace game::neural
