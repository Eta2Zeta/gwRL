#pragma once

#include <filesystem>
#include <map>
#include <string>
#include <string_view>
#include <variant>
#include <vector>

namespace game::json {

class Value {
  public:
    using Array = std::vector<Value>;
    using Object = std::map<std::string, Value>;
    using Storage = std::variant<std::nullptr_t, bool, double, std::string, Array, Object>;

    Value() : storage_(nullptr) {}
    Value(std::nullptr_t) : storage_(nullptr) {}
    Value(bool value) : storage_(value) {}
    Value(double value) : storage_(value) {}
    Value(std::string value) : storage_(std::move(value)) {}
    Value(Array value) : storage_(std::move(value)) {}
    Value(Object value) : storage_(std::move(value)) {}

    bool isNull() const;
    bool isBool() const;
    bool isNumber() const;
    bool isString() const;
    bool isArray() const;
    bool isObject() const;

    bool asBool() const;
    double asNumber() const;
    int asInt() const;
    const std::string& asString() const;
    const Array& asArray() const;
    const Object& asObject() const;

    const Value& require(const std::string& key) const;
    const Value* find(const std::string& key) const;

  private:
    Storage storage_;
};

Value parse(std::string_view text);
Value parseFile(const std::filesystem::path& filePath);

}  // namespace game::json
