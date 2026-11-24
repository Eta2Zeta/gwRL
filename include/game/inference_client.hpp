#pragma once

#include "game/search.hpp"

#include <cstdint>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace game::campaign {

// The inference server closed the pipe a game thread sends its requests through:
// the server has stopped, and the game cannot continue.
class InferenceClosed : public std::runtime_error {
  public:
    using std::runtime_error::runtime_error;
};

// One game thread's client of the inference server (SharedEvaluatorServer in
// studies/campaign/shared_evaluator.py). For each position it writes the zone
// input into the thread's shared-memory buffer, sends a short request through the
// thread's pipe and waits for the reply, all without Python. One request is in
// flight at a time, so the server reads the buffer before it is written again.
//
// A message on the pipe is a 4-byte big-endian length and that many bytes, as
// multiprocessing's Connection.send_bytes writes them. A request is, in
// little-endian order: a byte 1; the actor as a signed byte (0 Axis, 1 Allies,
// 2 Comintern, -1 for a chance position); the layout version's length, 2 bytes;
// the number of options, 4 bytes; the 13 fields' lengths in elements, 4 bytes
// each; then the layout version. The fields lie in the buffer one after another
// as 32-bit integers, in the order the network's input arrays name them:
// zone_index, zone_column, zone_value, global_column, global_value,
// action_offsets, action_column, action_value, action_source, action_target,
// path_offsets, path_zone, factor_groups. A reply is the number
// of options and the length of a network version, 4 bytes each; one prior per
// option and the three values, as 8-byte floats; then the network version, sent
// only when it differs from the last one this pipe was told.
//
// Several positions go in one request of kind 2 (evaluateMany): a byte 2, a
// zero byte, the layout version's length, 2 bytes, and the number of positions,
// 4 bytes; then for each position its actor, its number of options and its 13
// fields' lengths, 4 bytes each; then the layout version. Each position's fields
// lie in the buffer after the previous position's. Its reply is the number of
// positions and the length of a network version, 4 bytes each; for each
// position its number of options, 4 bytes, its priors and its three values; then
// the network version. Positions that do not all fit the buffer go in several
// requests, one after another.
class InferenceClient final : public SearchEvaluator {
  public:
    // The pipe end by its file descriptor, which stays the caller's, and the
    // shared memory by its name as multiprocessing.shared_memory gives it,
    // mapped up to `bytes` or the segment's own size, whichever is smaller.
    InferenceClient(int descriptor, const std::string& sharedMemoryName, std::size_t bytes);
    ~InferenceClient() override;
    InferenceClient(const InferenceClient&) = delete;
    InferenceClient& operator=(const InferenceClient&) = delete;

    void evaluate(const std::shared_ptr<const ZoneInput>& input, const std::string& layout, int actor,
                  std::size_t options, std::vector<double>& priors, SearchValues& values) override;
    void evaluateMany(const std::string& layout, const std::vector<SearchQuestion>& questions,
                      std::vector<SearchAnswer>& answers) override;
    // Unmaps the buffer; later evaluations fail.
    void close();

    // The version of the networks that answered last, once the server has named one.
    const std::optional<std::string>& networkVersion() const { return networkVersion_; }
    std::uint64_t requests() const { return requests_; }        // Requests sent, of one position or several.
    std::uint64_t evaluations() const { return evaluations_; }  // Positions asked about.
    double prepareSeconds() const { return prepareSeconds_; }  // Writing the input and sending the request.
    double waitSeconds() const { return waitSeconds_; }        // From the request sent to the reply read.

  private:
    void writeAll(const unsigned char* data, std::size_t size);
    void readAll(unsigned char* data, std::size_t size);
    int descriptor_;
    unsigned char* buffer_{nullptr};
    std::size_t bytes_{0};
    std::optional<std::string> networkVersion_;
    std::vector<unsigned char> message_;
    std::uint64_t requests_{0};
    std::uint64_t evaluations_{0};
    double prepareSeconds_{0.0};
    double waitSeconds_{0.0};
};

}  // namespace game::campaign
