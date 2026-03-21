#pragma once

#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace game {

enum class UnitKind {
    Infantry,
    Artillery,
    Marine,
    Fighter,
    Transport,
};

inline std::string_view toString(UnitKind kind) {
    switch (kind) {
        case UnitKind::Infantry:
            return "Infantry";
        case UnitKind::Artillery:
            return "Artillery";
        case UnitKind::Marine:
            return "Marine";
        case UnitKind::Fighter:
            return "Fighter";
        case UnitKind::Transport:
            return "Transport";
    }
    throw std::runtime_error("Unknown unit kind");
}

inline UnitKind parseUnitKind(std::string_view value) {
    if (value == "Infantry") {
        return UnitKind::Infantry;
    }
    if (value == "Artillery") {
        return UnitKind::Artillery;
    }
    if (value == "Marine") {
        return UnitKind::Marine;
    }
    if (value == "Fighter") {
        return UnitKind::Fighter;
    }
    if (value == "Transport") {
        return UnitKind::Transport;
    }
    throw std::runtime_error("Unsupported unit kind: " + std::string(value));
}

class Unit {
  public:
    Unit(UnitKind kind, std::string ownerId, std::string zoneId, int maxMovement)
        : kind_(kind),
          ownerId_(std::move(ownerId)),
          zoneId_(std::move(zoneId)),
          maxMovement_(maxMovement),
          movementLeft_(maxMovement) {}

    virtual ~Unit() = default;

    UnitKind kind() const { return kind_; }
    const std::string& ownerId() const { return ownerId_; }
    const std::string& zoneId() const { return zoneId_; }
    int maxMovement() const { return maxMovement_; }
    int movementLeft() const { return movementLeft_; }
    const std::optional<std::string>& pendingCombatTargetZoneId() const { return pendingCombatTargetZoneId_; }
    bool hasPendingCombatTarget() const { return pendingCombatTargetZoneId_.has_value(); }

    void setOwnerId(std::string ownerId) { ownerId_ = std::move(ownerId); }
    void setZoneId(std::string zoneId) { zoneId_ = std::move(zoneId); }
    void setPendingCombatTargetZoneId(std::string zoneId) { pendingCombatTargetZoneId_ = std::move(zoneId); }
    void clearPendingCombatTargetZoneId() { pendingCombatTargetZoneId_.reset(); }
    void resetMovement() { movementLeft_ = maxMovement_; }
    virtual bool canCarryCargo() const { return false; }
    virtual const std::vector<UnitKind>& cargo() const {
        static const std::vector<UnitKind> emptyCargo;
        return emptyCargo;
    }
    virtual void setCargo(std::vector<UnitKind> cargo) {
        if (!cargo.empty()) {
            throw std::runtime_error("This unit cannot carry cargo");
        }
    }

    void spendMovement(int amount) {
        if (amount < 0) {
            throw std::runtime_error("Movement spend cannot be negative");
        }
        if (amount > movementLeft_) {
            throw std::runtime_error("Unit does not have enough movement left");
        }
        movementLeft_ -= amount;
    }

    virtual std::unique_ptr<Unit> clone() const = 0;

  protected:
    UnitKind kind_;
    std::string ownerId_;
    std::string zoneId_;
    std::optional<std::string> pendingCombatTargetZoneId_;
    int maxMovement_ {0};
    int movementLeft_ {0};
};

class Infantry final : public Unit {
  public:
    Infantry(std::string ownerId, std::string zoneId)
        : Unit(UnitKind::Infantry, std::move(ownerId), std::move(zoneId), 1) {}

    std::unique_ptr<Unit> clone() const override { return std::make_unique<Infantry>(*this); }
};

class Artillery final : public Unit {
  public:
    Artillery(std::string ownerId, std::string zoneId)
        : Unit(UnitKind::Artillery, std::move(ownerId), std::move(zoneId), 1) {}

    std::unique_ptr<Unit> clone() const override { return std::make_unique<Artillery>(*this); }
};

class Marine final : public Unit {
  public:
    Marine(std::string ownerId, std::string zoneId)
        : Unit(UnitKind::Marine, std::move(ownerId), std::move(zoneId), 1) {}

    std::unique_ptr<Unit> clone() const override { return std::make_unique<Marine>(*this); }
};

class Fighter final : public Unit {
  public:
    Fighter(std::string ownerId, std::string zoneId)
        : Unit(UnitKind::Fighter, std::move(ownerId), std::move(zoneId), 4) {}

    std::unique_ptr<Unit> clone() const override { return std::make_unique<Fighter>(*this); }
};

class Transport final : public Unit {
  public:
    static constexpr std::size_t kMaxCargo = 2;

    Transport(std::string ownerId, std::string zoneId)
        : Unit(UnitKind::Transport, std::move(ownerId), std::move(zoneId), 2) {}

    bool canCarryCargo() const override { return true; }
    const std::vector<UnitKind>& cargo() const override { return cargo_; }

    void setCargo(std::vector<UnitKind> cargo) override {
        if (cargo.size() > kMaxCargo) {
            throw std::runtime_error("Transport cargo cannot exceed 2 units");
        }
        cargo_ = std::move(cargo);
    }

    std::unique_ptr<Unit> clone() const override { return std::make_unique<Transport>(*this); }

  private:
    std::vector<UnitKind> cargo_;
};

inline std::unique_ptr<Unit> makeUnit(UnitKind kind, std::string ownerId, std::string zoneId) {
    switch (kind) {
        case UnitKind::Infantry:
            return std::make_unique<Infantry>(std::move(ownerId), std::move(zoneId));
        case UnitKind::Artillery:
            return std::make_unique<Artillery>(std::move(ownerId), std::move(zoneId));
        case UnitKind::Marine:
            return std::make_unique<Marine>(std::move(ownerId), std::move(zoneId));
        case UnitKind::Fighter:
            return std::make_unique<Fighter>(std::move(ownerId), std::move(zoneId));
        case UnitKind::Transport:
            return std::make_unique<Transport>(std::move(ownerId), std::move(zoneId));
    }
    throw std::runtime_error("Unable to build unit");
}

inline int purchaseCost(UnitKind kind) {
    switch (kind) {
        case UnitKind::Infantry:
            return 3;
        case UnitKind::Artillery:
            return 4;
        case UnitKind::Fighter:
            return 10;
        case UnitKind::Marine:
        case UnitKind::Transport:
            return -1;
    }
    throw std::runtime_error("Unknown unit kind for purchase cost");
}

}  // namespace game
