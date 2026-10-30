#include "game/campaign.hpp"

#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}
void rejects(const std::function<void()>& action) {
    try { action(); } catch (const std::exception&) { return; }
    throw std::runtime_error("Invalid JSON accepted");
}
}

int main() {
    try {
        using namespace game;
        for (bool portAttack : {false, true}) {
            const json::Value context(portAttack ? "port_attack" : "standard");
            require(context.isString() && context.asString() == (portAttack ? "port_attack" : "standard"),
                    "Rule continuation string converted silently to a boolean");
        }
        require(json::Value(true).isBool() && json::Value(nullptr).isNull(), "String overload changed boolean/null types");
        const char* missing = nullptr;
        rejects([&] { json::Value value(missing); });
        std::cout << "PASS rule continuation string types\n";
        for (const auto& text : std::vector<std::string> {
                R"({"a":1,"a":2})", R"({"a":{"b":1,"b":2}})",
                "1e309", "-1e309", "01", "-01", "1.", "+1", "NaN", "[1,]",
                R"("\uD800")", R"("\uDC00")", R"("\uD800\u0041")", R"("\uZZZZ")",
                std::string("\"raw\ncontrol\""), std::string("\vnull")}) {
            rejects([&] { json::parse(text); });
        }
        std::cout << "PASS malformed documents and duplicate keys\n";
        const auto decoded = json::parse(R"({"name":"\u4e2d\u56fd","symbol":"\ud83c\udfb2","zero":"\u0000"})");
        require(decoded.require("name").asString() == "中国", "BMP Unicode decode failed");
        require(decoded.require("symbol").asString() == "🎲", "Surrogate pair decode failed");
        require(decoded.require("zero").asString() == std::string(1, '\0'), "NUL decode failed");
        require(campaign::canonicalJson(json::parse(campaign::canonicalJson(decoded))) == campaign::canonicalJson(decoded),
                "Canonical JSON does not round trip Unicode/control characters");
        std::cout << "PASS Unicode and canonical control-character round trip\n";
        require(json::parse("2147483647").asInt() == std::numeric_limits<int>::max(), "Int max changed");
        require(json::parse("-2147483648").asInt() == std::numeric_limits<int>::min(), "Int min changed");
        for (const auto& text : {"2147483648", "-2147483649", "1.25", "1e100"}) {
            rejects([&] { json::parse(text).asInt(); });
        }
        std::cout << "PASS integer range and fractional rejection\n";
        json::Value::Object fields;
        fields.emplace("nested", json::Value(json::Value::Array{json::Value(1.0)}));
        json::Value holder(std::move(fields));
        const auto* nested = &holder.asObject().at("nested");
        const auto moved = std::move(holder).asObject();
        require(&moved.at("nested") == nested, "A temporary copied its object instead of giving it up");
        rejects([] { json::Value(1.0).asObject(); });
        std::cout << "PASS temporaries give up their objects\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL JSON integrity: " << error.what() << '\n';
        return 1;
    }
}
