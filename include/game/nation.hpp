#pragma once

#include <string>

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

    void setIncome(int income) { income_ = income; }
    void setMaxFactoryOutput(int maxFactoryOutput) { maxFactoryOutput_ = maxFactoryOutput; }
    void setTreasury(int treasury) { treasury_ = treasury; }

  private:
    std::string id_;
    std::string displayName_;
    int income_ {0};
    int maxFactoryOutput_ {0};
    int treasury_ {0};
};

}  // namespace game
