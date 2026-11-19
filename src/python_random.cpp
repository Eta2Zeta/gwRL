#include "game/python_random.hpp"

#include <algorithm>
#include <bit>
#include <cmath>
#include <numbers>
#include <stdexcept>

// Python never fuses a multiplication and an addition into one rounding, so
// neither may this file (clang otherwise fuses within an expression).
#if defined(__clang__)
#pragma clang fp contract(off)
#elif defined(__GNUC__)
#pragma GCC optimize("fp-contract=off")
#endif

namespace game::campaign {
namespace {
constexpr int N = 624;
constexpr int M = 397;
constexpr std::uint32_t matrixA = 0x9908b0dfU;
constexpr std::uint32_t upperMask = 0x80000000U;
constexpr std::uint32_t lowerMask = 0x7fffffffU;
}  // namespace

PythonRandom::PythonRandom(std::uint64_t seed) {
    // random_seed: the seed's 32-bit words from the least significant, as many
    // as its bits need and at least one; then init_by_array.
    const std::uint32_t key[2] = {static_cast<std::uint32_t>(seed), static_cast<std::uint32_t>(seed >> 32)};
    const std::size_t keyLength = (seed >> 32) != 0 ? 2 : 1;
    auto& mt = state_;
    mt[0] = 19650218U;  // init_genrand(19650218)
    for (int i = 1; i < N; ++i)
        mt[i] = 1812433253U * (mt[i - 1] ^ (mt[i - 1] >> 30)) + static_cast<std::uint32_t>(i);
    index_ = N;
    std::size_t i = 1, j = 0;
    for (std::size_t k = std::max<std::size_t>(N, keyLength); k; --k) {
        mt[i] = (mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1664525U)) + key[j] + static_cast<std::uint32_t>(j);
        ++i;
        ++j;
        if (i >= N) {
            mt[0] = mt[N - 1];
            i = 1;
        }
        if (j >= keyLength) j = 0;
    }
    for (std::size_t k = N - 1; k; --k) {
        mt[i] = (mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1566083941U)) - static_cast<std::uint32_t>(i);
        ++i;
        if (i >= N) {
            mt[0] = mt[N - 1];
            i = 1;
        }
    }
    mt[0] = 0x80000000U;
}

std::uint32_t PythonRandom::next32() {
    auto& mt = state_;
    if (index_ >= N) {
        const auto twist = [&](int to, int a, int b, int c) {
            const std::uint32_t y = (mt[a] & upperMask) | (mt[b] & lowerMask);
            mt[to] = mt[c] ^ (y >> 1) ^ ((y & 1U) ? matrixA : 0U);
        };
        int k = 0;
        for (; k < N - M; ++k) twist(k, k, k + 1, k + M);
        for (; k < N - 1; ++k) twist(k, k, k + 1, k + (M - N));
        twist(N - 1, N - 1, 0, M - 1);
        index_ = 0;
    }
    std::uint32_t y = mt[index_++];
    y ^= (y >> 11);
    y ^= (y << 7) & 0x9d2c5680U;
    y ^= (y << 15) & 0xefc60000U;
    y ^= (y >> 18);
    return y;
}

double PythonRandom::random() {
    const std::uint32_t a = next32() >> 5;
    const std::uint32_t b = next32() >> 6;
    return (a * 67108864.0 + b) * (1.0 / 9007199254740992.0);
}

std::uint32_t PythonRandom::getrandbits(int bits) {
    if (bits < 0 || bits > 32) throw std::invalid_argument("getrandbits takes 0 to 32 bits here");
    if (bits == 0) return 0;
    return next32() >> (32 - bits);
}

std::uint64_t PythonRandom::getrandbits64() {
    // Words from the least significant.
    const std::uint64_t low = next32();
    const std::uint64_t high = next32();
    return (high << 32) | low;
}

std::uint32_t PythonRandom::randbelow(std::uint32_t n) {
    if (n == 0) throw std::invalid_argument("randbelow needs a positive bound");
    const int bits = std::bit_width(n);
    std::uint32_t r = getrandbits(bits);
    while (r >= n) r = getrandbits(bits);
    return r;
}

double PythonRandom::gammavariate(double alpha, double beta) {
    if (alpha <= 0.0 || beta <= 0.0) throw std::invalid_argument("gammavariate: alpha and beta must be > 0.0");
    if (alpha > 1.0) {
        // R.C.H. Cheng, as Lib/random.py has it.
        const double log4 = std::log(4.0);
        const double sgMagic = 1.0 + std::log(4.5);
        const double ainv = std::sqrt(2.0 * alpha - 1.0);
        const double bbb = alpha - log4;
        const double ccc = alpha + ainv;
        while (true) {
            const double u1 = random();
            if (!(1e-7 < u1 && u1 < 0.9999999)) continue;
            const double u2 = 1.0 - random();
            const double v = std::log(u1 / (1.0 - u1)) / ainv;
            const double x = alpha * std::exp(v);
            const double z = u1 * u1 * u2;
            const double r = bbb + ccc * v - x;
            if (r + sgMagic - 4.5 * z >= 0.0 || r >= std::log(z)) return x * beta;
        }
    }
    if (alpha == 1.0) return -std::log(1.0 - random()) * beta;
    // Algorithm GS of Kennedy and Gentle, as Lib/random.py has it.
    constexpr double e = std::numbers::e;
    double x;
    while (true) {
        const double u = random();
        const double b = (e + alpha) / e;
        const double p = b * u;
        if (p <= 1.0)
            x = std::pow(p, 1.0 / alpha);
        else
            x = -std::log((b - p) / alpha);
        const double u1 = random();
        if (p > 1.0) {
            if (u1 <= std::pow(x, alpha - 1.0)) break;
        } else if (u1 <= std::exp(-x)) {
            break;
        }
    }
    return x * beta;
}

double pythonSum(const double* values, std::size_t count) {
    if (count == 0) return 0.0;
    // The integer start 0 plus the first float is that float; the rest are
    // added with Neumaier's compensation (Python/bltinmodule.c, builtin_sum_impl).
    double result = 0.0 + values[0];
    double compensation = 0.0;
    for (std::size_t i = 1; i < count; ++i) {
        const double x = values[i];
        const double t = result + x;
        if (std::fabs(result) >= std::fabs(x))
            compensation += (result - t) + x;
        else
            compensation += (x - t) + result;
        result = t;
    }
    if (compensation != 0.0 && std::isfinite(compensation)) result += compensation;
    return result;
}

}  // namespace game::campaign
