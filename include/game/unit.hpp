#pragma once

#include <memory>
#include <stdexcept>
#include <string>
#include <string_view>

namespace game {

enum class UnitKind {
    Infantry,
    Marine,
    Fighter,
    Transport,
};

inline std::string_view toString(UnitKind kind) {
    switch (kind) {
        case UnitKind::Infantry:
            return "Infantry";
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

    void setZoneId(std::string zoneId) { zoneId_ = std::move(zoneId); }
    void resetMovement() { movementLeft_ = maxMovement_; }

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
    int maxMovement_ {0};
    int movementLeft_ {0};
};

class Infantry final : public Unit {
  public:
    Infantry(std::string ownerId, std::string zoneId)
        : Unit(UnitKind::Infantry, std::move(ownerId), std::move(zoneId), 1) {}

    std::unique_ptr<Unit> clone() const override { return std::make_unique<Infantry>(*this); }
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
    Transport(std::string ownerId, std::string zoneId)
        : Unit(UnitKind::Transport, std::move(ownerId), std::move(zoneId), 2) {}

    std::unique_ptr<Unit> clone() const override { return std::make_unique<Transport>(*this); }
};

inline std::unique_ptr<Unit> makeUnit(UnitKind kind, std::string ownerId, std::string zoneId) {
    switch (kind) {
        case UnitKind::Infantry:
            return std::make_unique<Infantry>(std::move(ownerId), std::move(zoneId));
        case UnitKind::Marine:
            return std::make_unique<Marine>(std::move(ownerId), std::move(zoneId));
        case UnitKind::Fighter:
            return std::make_unique<Fighter>(std::move(ownerId), std::move(zoneId));
        case UnitKind::Transport:
            return std::make_unique<Transport>(std::move(ownerId), std::move(zoneId));
    }
    throw std::runtime_error("Unable to build unit");
}

}  // namespace game
