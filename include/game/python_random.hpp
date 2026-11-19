#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace game::campaign {

// Python's random.Random, bit for bit (CPython 3.13: Modules/_randommodule.c and
// Lib/random.py): the Mersenne Twister seeded from an integer by init_by_array,
// and the draws the search makes from it. The C++ search (game/search.hpp) draws
// exactly what the Python search (studies/shared/multiplayer_mcts.py) draws, so
// the two can be compared choice by choice.
class PythonRandom {
  public:
    // random.Random(seed), for an integer seed from 0 to 2**64 - 1.
    explicit PythonRandom(std::uint64_t seed);
    std::uint32_t next32();                    // One output of the generator (genrand_uint32).
    double random();                           // random.random()
    std::uint32_t getrandbits(int bits);       // random.getrandbits(bits), for 0 <= bits <= 32
    std::uint64_t getrandbits64();             // random.getrandbits(64)
    std::uint32_t randbelow(std::uint32_t n);  // random.randrange(n), for n >= 1
    double gammavariate(double alpha, double beta);

  private:
    std::array<std::uint32_t, 624> state_{};
    int index_{624};
};

// Python's built-in sum() of a list of floats (CPython 3.12 and later): Neumaier's
// compensated summation, whose compensation is added once at the end. An empty
// list sums to zero.
double pythonSum(const double* values, std::size_t count);

}  // namespace game::campaign
