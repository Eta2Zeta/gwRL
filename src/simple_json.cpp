#include "game/simple_json.hpp"

#include <cctype>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace game::json {

namespace {

class Parser {
  public:
    explicit Parser(std::string_view input) : input_(input) {}

    Value parseDocument() {
        skipWhitespace();
        Value value = parseValue();
        skipWhitespace();
        if (!isAtEnd()) {
            throw std::runtime_error("Unexpected trailing content in JSON");
        }
        return value;
    }

  private:
    Value parseValue() {
        skipWhitespace();
        if (isAtEnd()) {
            throw std::runtime_error("Unexpected end of JSON");
        }

        const char current = peek();
        if (current == '{') {
            return parseObject();
        }
        if (current == '[') {
            return parseArray();
        }
        if (current == '"') {
            return Value(parseString());
        }
        if (current == 't') {
            consumeLiteral("true");
            return Value(true);
        }
        if (current == 'f') {
            consumeLiteral("false");
            return Value(false);
        }
        if (current == 'n') {
            consumeLiteral("null");
            return Value(nullptr);
        }
        if (current == '-' || std::isdigit(static_cast<unsigned char>(current))) {
            return Value(parseNumber());
        }

        throw std::runtime_error(std::string("Unexpected JSON token: ") + current);
    }

    Value::Object parseObject() {
        consume('{');
        skipWhitespace();

        Value::Object object;
        if (tryConsume('}')) {
            return object;
        }

        while (true) {
            skipWhitespace();
            std::string key = parseString();
            skipWhitespace();
            consume(':');
            object.emplace(std::move(key), parseValue());
            skipWhitespace();
            if (tryConsume('}')) {
                return object;
            }
            consume(',');
        }
    }

    Value::Array parseArray() {
        consume('[');
        skipWhitespace();

        Value::Array array;
        if (tryConsume(']')) {
            return array;
        }

        while (true) {
            array.push_back(parseValue());
            skipWhitespace();
            if (tryConsume(']')) {
                return array;
            }
            consume(',');
        }
    }

    std::string parseString() {
        consume('"');

        std::string value;
        while (!isAtEnd()) {
            const char current = advance();
            if (current == '"') {
                return value;
            }
            if (current == '\\') {
                if (isAtEnd()) {
                    throw std::runtime_error("Unterminated escape sequence in JSON string");
                }
                const char escaped = advance();
                switch (escaped) {
                    case '"':
                    case '\\':
                    case '/':
                        value.push_back(escaped);
                        break;
                    case 'b':
                        value.push_back('\b');
                        break;
                    case 'f':
                        value.push_back('\f');
                        break;
                    case 'n':
                        value.push_back('\n');
                        break;
                    case 'r':
                        value.push_back('\r');
                        break;
                    case 't':
                        value.push_back('\t');
                        break;
                    case 'u':
                        throw std::runtime_error("Unicode escape sequences are not supported in this setup parser");
                    default:
                        throw std::runtime_error("Unsupported escape sequence in JSON string");
                }
                continue;
            }
            value.push_back(current);
        }

        throw std::runtime_error("Unterminated JSON string");
    }

    double parseNumber() {
        const std::size_t start = index_;

        if (peek() == '-') {
            advance();
        }

        consumeDigits();

        if (!isAtEnd() && peek() == '.') {
            advance();
            consumeDigits();
        }

        if (!isAtEnd() && (peek() == 'e' || peek() == 'E')) {
            advance();
            if (!isAtEnd() && (peek() == '+' || peek() == '-')) {
                advance();
            }
            consumeDigits();
        }

        const std::string token(input_.substr(start, index_ - start));
        char* end = nullptr;
        const double value = std::strtod(token.c_str(), &end);
        if (end == token.c_str() || *end != '\0') {
            throw std::runtime_error("Invalid JSON number: " + token);
        }
        return value;
    }

    void consumeDigits() {
        if (isAtEnd() || !std::isdigit(static_cast<unsigned char>(peek()))) {
            throw std::runtime_error("Expected digits in JSON number");
        }
        while (!isAtEnd() && std::isdigit(static_cast<unsigned char>(peek()))) {
            advance();
        }
    }

    void consumeLiteral(std::string_view literal) {
        for (char expected : literal) {
            consume(expected);
        }
    }

    void skipWhitespace() {
        while (!isAtEnd() && std::isspace(static_cast<unsigned char>(peek()))) {
            ++index_;
        }
    }

    bool tryConsume(char expected) {
        if (!isAtEnd() && peek() == expected) {
            ++index_;
            return true;
        }
        return false;
    }

    void consume(char expected) {
        if (isAtEnd() || peek() != expected) {
            throw std::runtime_error(std::string("Expected '") + expected + "' in JSON");
        }
        ++index_;
    }

    char advance() {
        if (isAtEnd()) {
            throw std::runtime_error("Unexpected end of JSON");
        }
        return input_[index_++];
    }

    char peek() const { return input_[index_]; }

    bool isAtEnd() const { return index_ >= input_.size(); }

    std::string_view input_;
    std::size_t index_ {0};
};

}  // namespace

bool Value::isNull() const { return std::holds_alternative<std::nullptr_t>(storage_); }
bool Value::isBool() const { return std::holds_alternative<bool>(storage_); }
bool Value::isNumber() const { return std::holds_alternative<double>(storage_); }
bool Value::isString() const { return std::holds_alternative<std::string>(storage_); }
bool Value::isArray() const { return std::holds_alternative<Array>(storage_); }
bool Value::isObject() const { return std::holds_alternative<Object>(storage_); }

bool Value::asBool() const {
    if (!isBool()) {
        throw std::runtime_error("JSON value is not a bool");
    }
    return std::get<bool>(storage_);
}

double Value::asNumber() const {
    if (!isNumber()) {
        throw std::runtime_error("JSON value is not a number");
    }
    return std::get<double>(storage_);
}

int Value::asInt() const {
    const double value = asNumber();
    if (std::floor(value) != value) {
        throw std::runtime_error("JSON number is not an integer");
    }
    return static_cast<int>(value);
}

const std::string& Value::asString() const {
    if (!isString()) {
        throw std::runtime_error("JSON value is not a string");
    }
    return std::get<std::string>(storage_);
}

const Value::Array& Value::asArray() const {
    if (!isArray()) {
        throw std::runtime_error("JSON value is not an array");
    }
    return std::get<Array>(storage_);
}

const Value::Object& Value::asObject() const {
    if (!isObject()) {
        throw std::runtime_error("JSON value is not an object");
    }
    return std::get<Object>(storage_);
}

const Value& Value::require(const std::string& key) const {
    const auto* value = find(key);
    if (!value) {
        throw std::runtime_error("Missing required JSON key: " + key);
    }
    return *value;
}

const Value* Value::find(const std::string& key) const {
    if (!isObject()) {
        throw std::runtime_error("JSON value is not an object");
    }
    const auto& object = std::get<Object>(storage_);
    auto it = object.find(key);
    if (it == object.end()) {
        return nullptr;
    }
    return &it->second;
}

Value parse(std::string_view text) {
    Parser parser(text);
    return parser.parseDocument();
}

Value parseFile(const std::filesystem::path& filePath) {
    std::ifstream input(filePath);
    if (!input) {
        throw std::runtime_error("Unable to open JSON file: " + filePath.string());
    }

    std::ostringstream buffer;
    buffer << input.rdbuf();
    return parse(buffer.str());
}

}  // namespace game::json
