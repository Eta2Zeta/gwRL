#include "game/inference_client.hpp"

#include <algorithm>
#include <array>
#include <cerrno>
#include <chrono>
#include <cstring>
#include <system_error>

#ifndef _WIN32
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

namespace game::campaign {
namespace {

using SteadyClock = std::chrono::steady_clock;

constexpr std::size_t fieldCount = 13;
constexpr std::size_t requestHeader = 8 + 4 * fieldCount;
constexpr std::size_t replyHeader = 8;

std::array<const std::vector<std::int32_t>*, fieldCount> fields(const ZoneInput& z) {
    return {&z.zoneIndex, &z.zoneColumn, &z.zoneValue, &z.globalColumn, &z.globalValue, &z.actionOffsets,
            &z.actionColumn, &z.actionValue, &z.actionSource, &z.actionTarget, &z.pathOffsets, &z.pathZone,
            &z.factorGroups};
}

void put16(unsigned char* to, std::uint16_t value) {
    to[0] = static_cast<unsigned char>(value);
    to[1] = static_cast<unsigned char>(value >> 8);
}

void put32(unsigned char* to, std::uint32_t value) {
    for (int i = 0; i < 4; ++i) to[i] = static_cast<unsigned char>(value >> (8 * i));
}

std::uint32_t get32(const unsigned char* from) {
    std::uint32_t value = 0;
    for (int i = 0; i < 4; ++i) value |= static_cast<std::uint32_t>(from[i]) << (8 * i);
    return value;
}

double getDouble(const unsigned char* from) {
    std::uint64_t bits = 0;
    for (int i = 0; i < 8; ++i) bits |= static_cast<std::uint64_t>(from[i]) << (8 * i);
    double value;
    std::memcpy(&value, &bits, sizeof value);
    return value;
}

double seconds(SteadyClock::duration duration) { return std::chrono::duration<double>(duration).count(); }

}  // namespace

#ifdef _WIN32

InferenceClient::InferenceClient(int, const std::string&, std::size_t) : descriptor_(-1) {
    throw std::runtime_error("The native inference client needs POSIX pipes and shared memory");
}
InferenceClient::~InferenceClient() = default;
void InferenceClient::close() {}
void InferenceClient::writeAll(const unsigned char*, std::size_t) {}
void InferenceClient::readAll(unsigned char*, std::size_t) {}
void InferenceClient::evaluate(const std::shared_ptr<const ZoneInput>&, const std::string&, int, std::size_t,
                               std::vector<double>&, SearchValues&) {
    throw std::runtime_error("The native inference client needs POSIX pipes and shared memory");
}

#else

InferenceClient::InferenceClient(int descriptor, const std::string& sharedMemoryName, std::size_t bytes)
    : descriptor_(descriptor), bytes_(bytes) {
    if (descriptor < 0) throw std::invalid_argument("The inference client needs an open pipe");
    if (sharedMemoryName.empty() || bytes == 0) throw std::invalid_argument("The inference client needs a shared buffer");
    // multiprocessing.shared_memory names a POSIX segment without its leading slash.
    const auto name = sharedMemoryName.front() == '/' ? sharedMemoryName : "/" + sharedMemoryName;
    const int memory = ::shm_open(name.c_str(), O_RDWR, 0600);
    if (memory < 0) throw std::system_error(errno, std::generic_category(), "Cannot open the shared buffer " + name);
    // At most the segment's own size, as Python maps it.
    struct stat info {};
    if (::fstat(memory, &info) == 0 && info.st_size > 0) bytes_ = std::min(bytes_, static_cast<std::size_t>(info.st_size));
    void* mapped = ::mmap(nullptr, bytes_, PROT_READ | PROT_WRITE, MAP_SHARED, memory, 0);
    const int mapError = errno;
    ::close(memory);
    if (mapped == MAP_FAILED) throw std::system_error(mapError, std::generic_category(), "Cannot map the shared buffer " + name);
    buffer_ = static_cast<unsigned char*>(mapped);
}

InferenceClient::~InferenceClient() { close(); }

void InferenceClient::close() {
    if (buffer_) ::munmap(buffer_, bytes_);
    buffer_ = nullptr;
}

void InferenceClient::writeAll(const unsigned char* data, std::size_t size) {
    while (size) {
        const auto written = ::write(descriptor_, data, size);
        if (written < 0) {
            if (errno == EINTR) continue;
            if (errno == EPIPE || errno == ECONNRESET || errno == EBADF)
                throw InferenceClosed("The shared evaluator closed this game thread's pipe");
            throw std::system_error(errno, std::generic_category(), "Cannot send an inference request");
        }
        data += written;
        size -= static_cast<std::size_t>(written);
    }
}

void InferenceClient::readAll(unsigned char* data, std::size_t size) {
    while (size) {
        const auto read = ::read(descriptor_, data, size);
        if (read == 0) throw InferenceClosed("The shared evaluator closed this game thread's pipe");
        if (read < 0) {
            if (errno == EINTR) continue;
            if (errno == ECONNRESET || errno == EBADF) throw InferenceClosed("The shared evaluator closed this game thread's pipe");
            throw std::system_error(errno, std::generic_category(), "Cannot read an inference reply");
        }
        data += read;
        size -= static_cast<std::size_t>(read);
    }
}

void InferenceClient::evaluate(const std::shared_ptr<const ZoneInput>& input, const std::string& layout, int actor,
                               std::size_t options, std::vector<double>& priors, SearchValues& values) {
    if (!buffer_) throw InferenceClosed("The inference client is closed");
    if (!input) throw std::invalid_argument("The inference server needs the position's zone input");
    if (input->actionCount() != options) throw std::invalid_argument("The zone input does not list the requested options");
    if (actor < -1 || actor > 2) throw std::invalid_argument("Unknown campaign decision player");
    if (layout.size() > 0xFFFF) throw std::invalid_argument("The layout version is too long");
    const auto started = SteadyClock::now();
    const auto parts = fields(*input);
    std::size_t offset = 0;
    for (const auto* part : parts) {
        const auto size = part->size() * sizeof(std::int32_t);
        if (offset + size > bytes_) throw std::length_error("A decision's zone input does not fit its shared buffer");
        if (size) std::memcpy(buffer_ + offset, part->data(), size);
        offset += size;
    }
    message_.assign(4 + requestHeader + layout.size(), 0);
    const auto payload = static_cast<std::uint32_t>(requestHeader + layout.size());
    for (int i = 0; i < 4; ++i) message_[static_cast<std::size_t>(i)] = static_cast<unsigned char>(payload >> (8 * (3 - i)));
    unsigned char* request = message_.data() + 4;
    request[0] = 1;
    request[1] = static_cast<unsigned char>(static_cast<std::int8_t>(actor));
    put16(request + 2, static_cast<std::uint16_t>(layout.size()));
    put32(request + 4, static_cast<std::uint32_t>(options));
    for (std::size_t i = 0; i < fieldCount; ++i) put32(request + 8 + 4 * i, static_cast<std::uint32_t>(parts[i]->size()));
    std::memcpy(request + requestHeader, layout.data(), layout.size());
    writeAll(message_.data(), message_.size());
    const auto sent = SteadyClock::now();

    unsigned char length[4];
    readAll(length, 4);
    const std::uint32_t size = (std::uint32_t{length[0]} << 24) | (std::uint32_t{length[1]} << 16) |
                               (std::uint32_t{length[2]} << 8) | std::uint32_t{length[3]};
    if (size < replyHeader || size > (1U << 30)) throw std::runtime_error("The inference server sent a malformed reply");
    message_.resize(size);
    readAll(message_.data(), size);
    const auto count = get32(message_.data());
    const auto versionLength = get32(message_.data() + 4);
    if (count != options) throw std::invalid_argument("The shared evaluator returned a different legal menu");
    if (size != replyHeader + 8 * (static_cast<std::size_t>(count) + 3) + versionLength)
        throw std::runtime_error("The inference server sent a malformed reply");
    const unsigned char* at = message_.data() + replyHeader;
    priors.resize(count);
    for (std::uint32_t i = 0; i < count; ++i, at += 8) priors[i] = getDouble(at);
    for (std::size_t c = 0; c < 3; ++c, at += 8) values[c] = getDouble(at);
    if (versionLength) networkVersion_.emplace(reinterpret_cast<const char*>(at), versionLength);
    ++requests_;
    prepareSeconds_ += seconds(sent - started);
    waitSeconds_ += seconds(SteadyClock::now() - sent);
}

#endif

}  // namespace game::campaign
