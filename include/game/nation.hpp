#pragma once

#include <algorithm>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_set>
#include <vector>

namespace game {

class Nation {
  public:
    Nation() = default;

    Nation(std::string id, std::string displayName, int income, int maxFactoryOutput, int treasury = -1)
        : id_(std::move(id)),
          displayName_(std::move(displayName)),
          income_(income),
          maxFactoryOutput_(maxFactoryOutput),
          treasury_(treasury >= 0 ? treasury : income) {}

    const std::string& id() const { return id_; }
    const std::string& displayName() const { return displayName_; }
    int income() const { return income_; }
    int maxFactoryOutput() const { return maxFactoryOutput_; }
    int treasury() const { return treasury_; }
    std::vector<std::string> atWarWith() const { return sortedValues(atWarWith_); }
    std::vector<std::string> allies() const { return sortedValues(allies_); }

    void setIncome(int income) { income_ = income; }
    void setMaxFactoryOutput(int maxFactoryOutput) { maxFactoryOutput_ = maxFactoryOutput; }
    void setTreasury(int treasury) { treasury_ = treasury; }
    void setAtWarWith(std::vector<std::string> nationIds) { replaceSet(atWarWith_, std::move(nationIds)); }
    void setAllies(std::vector<std::string> nationIds) { replaceSet(allies_, std::move(nationIds)); }
    void addTreasury(int amount) { treasury_ += amount; }
    void spendTreasury(int amount) {
        if (amount < 0) {
            throw std::runtime_error("Treasury spend cannot be negative");
        }
        if (amount > treasury_) {
            throw std::runtime_error("Nation does not have enough treasury");
        }
        treasury_ -= amount;
    }

    bool isAtWarWith(std::string_view nationId) const {
        return atWarWith_.find(std::string(nationId)) != atWarWith_.end();
    }

    bool isAlliedWith(std::string_view nationId) const {
        return allies_.find(std::string(nationId)) != allies_.end();
    }

    void declareWarOn(std::string nationId) { atWarWith_.insert(std::move(nationId)); }
    void addAlly(std::string nationId) { allies_.insert(std::move(nationId)); }

  private:
    static std::vector<std::string> sortedValues(const std::unordered_set<std::string>& values) {
        std::vector<std::string> ordered(values.begin(), values.end());
        std::sort(ordered.begin(), ordered.end());
        return ordered;
    }

    static void replaceSet(std::unordered_set<std::string>& target, std::vector<std::string> values) {
        target.clear();
        for (auto& value : values) {
            target.insert(std::move(value));
        }
    }

    std::string id_;
    std::string displayName_;
    int income_ {0};
    int maxFactoryOutput_ {0};
    int treasury_ {0};
    std::unordered_set<std::string> atWarWith_;
    std::unordered_set<std::string> allies_;
};

}  // namespace game
