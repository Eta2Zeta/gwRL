"""Build the campaign coverage index from stable rule IDs and executable fixtures.

This indexes evidence; it does not infer runtime support from catalog records.
Each fixture is checked to exist and to be invoked by its executable's main.
"""
from pathlib import Path
import json
import re
import hashlib
import argparse
import os

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/reference/rules-ledger.md"
OUT = ROOT / "docs/reference"
JSON_OUTPUT = OUT / "runtime-coverage.json"
MARKDOWN_OUTPUT = OUT / "runtime-coverage.md"

def specs(text):
    return [x.strip() for x in text.split(";") if x.strip()]

def entry(handler, fixture):
    return {"handlers": specs(handler), "fixtures": specs(fixture)}

# Runtime entry points and focused executable functions, independently of the
# catalog-source transcription checks. Multiple clauses can share a fixture.
E = {}
def put(ids, handlers, fixtures):
    for number in ids:
        E[f"R{number:03}"] = entry(handlers, fixtures)

P="src/politics.cpp::"
W="src/politics_warlords.cpp::"
M="src/movement.cpp::"
L="src/land_combat.cpp::"
A="src/air.cpp::"
N="src/naval_combat.cpp::"
O="src/naval_operations.cpp::"
V="src/naval_movement.cpp::"
C="src/catalog.cpp::"
B="src/economy.cpp::"
F="src/politics_influence.cpp::"
R="src/campaign_runtime.cpp::"
T=lambda name,fn:f"tests/{name.removesuffix('_tests')}_tests.cpp::{fn}"
put([0,1,23],P+"originalNation;"+P+"politicallyFriendly;"+P+"atWarWithMajor",T("politics","initialIdentityAndHomeCountry"))
put([2],M+"landAccess;"+P+"politicallyFriendly",T("movement","hostileStopsAndOrigins")+";"+T("politics_warlords","truceConsentAndTiming"))
put([3],P+"captureLand;"+L+"beginLandBattle;"+N+"beginNavalBattle",T("politics_warlords","neutralNonparticipantsRelocateToNearestFriendlyLand")+";"+T("politics_warlords","neutralRelocationWithoutFriendlyLandUsesAdoptedElimination")+";"+T("land_combat","jointDefendersConsentAndDiceDispute")+";"+T("naval_combat","jointDefenseDisputeUsesEntitledPlayers"))
put([4],M+"validateRoute;"+A+"validateFlight",T("movement","directionalTerrain")+";"+T("air_integration","aircraftLaunchesFromCarrierAndReplaysCargoLinks"))
put([5,8,10,12],L+"landCombatStats;"+M+"borderApproach;"+M+"validateRoute",T("land_combat","terrainAndJapaneseModifiers")+";"+T("movement","directionalTerrain")+";"+T("movement","riverBanksAndImpassableRoads"))
put([6,18],"src/campaign_setup.cpp::loadScenario",T("campaign_setup","main"))
put([9],M+"validateRoute;"+L+"landCombatStats",T("movement","directionalTerrain")+";"+T("land_combat","terrainAndJapaneseModifiers")+";"+T("land_truce","noOriginTerrainLimitEliminatesAttackers"))
put([11],L+"citySurrounded;"+L+"landCombatStats",T("land_combat","cityRoundLimitAndRetreatChoice")+";"+T("land_combat","terrainAndJapaneseModifiers"))
put([14],M+"validateRoute",T("movement","narrowCrossings"))
put([15,127],L+"landCombatStats;"+L+"beginLandBattle",T("land_combat","fortificationConstrainsApproach")+";"+T("land_combat","attritionIsSeparateAndNoReturnFire"))
put([16],M+"supplyRoute;"+M+"inSupply",T("movement","seaRangeRefreshAndSharedPorts")+";"+T("movement","noSecondSeaLeg")+";"+T("movement","blockadeSurfaceOnly"))
put([19],R+"Engine::endPhase;src/campaign_objective.cpp::terminalReturns",T("campaign_runtime","fivePhasesAndElevenFullRounds")+";"+T("campaign_env","terminalThreeVector"))
put([20],P+"refreshPoliticalState",T("politics","oneChinaPointIsNotSurrenderBonus")+";"+T("politics","ownTurnEvolutionExceptionAndOptionalFactory"))
put([24],P+"recordLandAttack;"+W+"continueCombatPoliticalResolution",T("politics_warlords","temporaryWarlordDefenseDoesNotGrantControl"))
put([25,27],P+"incorporateNation;"+W+"continueCombatPoliticalResolution",T("politics_warlords","dadaoAlignment")+";"+T("politics_warlords","incorporationDoesNotCreateWarWithDadaosController"))
put([26,42],R+"Engine::endPhase;"+P+"PoliticsRules::finishTurn",T("campaign_runtime","fivePhasesAndElevenFullRounds")+";"+T("politics_influence","mongoliaRecruitmentIsIndependent")+";"+T("campaign_state","nationalityRoutingCalendarAndSnapshot"))
put([29,30,31],P+"recordLandAttack;"+W+"continueCombatPoliticalResolution;"+W+"applyWarlordChance",T("politics_warlords","wholeWarlordTable")+";"+T("politics_warlords","frozenNeighborsAndCheckpoint")+";"+T("politics_warlords","attacksAndDefeatedKmt")+";"+T("politics_warlords","invasionAlignsEveryWarlordBeforeTruce"))
put([33,34],P+"mayDeclareWar;"+P+"declareWar",T("politics","declarationGatesAndUnknownAccounting")+";"+T("politics","outOfTurnPriorityCheckpointAndClone"))
put([36],P+"surrenderNation;"+P+"refreshPoliticalState",T("politics","ccpNoUnitsIsNotSurrenderOrGameEnd")+";"+T("politics","directAxisDadaoSurvivesJapan")+";"+T("politics","japanSurrenderQueueBoundaryAndReplay"))
put([37],P+"surrenderNation;"+P+"PoliticsRules::applyChanceImpl",T("politics","japanSurrenderQueueBoundaryAndReplay"))
put([40],W+"continueCombatPoliticalResolution;"+W+"applyWarlordAction",T("politics_warlords","truceConsentAndTiming")+";"+T("politics_warlords","invasionAlignsEveryWarlordBeforeTruce"))
put([41],W+"terminateChineseTruce;"+L+"LandCombatRules::applyChance",T("land_truce","voluntarySharedRolesFollowTheActiveBreaker")+";"+T("land_truce","thirdPartyAutomaticSharedRolesFollowTheLandPossessor")+";"+T("land_truce","automaticTruceLowMoraleEliminatesWithoutAnEscape")+";"+T("land_truce","japaneseCaptureGiftCanEndAnExistingTruce"))
put([43],R+"Engine::step;"+R+"Engine::replay",T("campaign_runtime","replayAndRestoreAreExact"))
put([44,45],B+"beginEconomyTurn;"+B+"EconomyRules::applyChance",T("economy","research")+";"+T("catalog","technologyAndConstruction"))
put([46],M+"blitzPairValid;"+L+"landCombatStats;"+L+"registerAttritionBattle",T("land_combat","blitzPairingIsAnExplicitChoice")+";"+T("land_combat","attritionIsSeparateAndNoReturnFire")+";"+T("air_mission","artilleryCityBombingStaysAdjacentAndBypassesAirDefence"))
put([47],A+"beginAirDefence;"+A+"AirRules::applyChance;"+N+"navalCombatActions",T("air_mission","rocketRadarBeforeDamage")+";"+T("air_tests","interceptorAndEscortSimultaneous")+";"+T("naval_combat","shipScrambleAndSkeletonCrewExclusion"))
put([48],N+"applyNavalCombatChance",T("naval_combat","aswTransportDefendsOnlySubmarines")+";"+T("naval_combat","seaplaneAswBonusTargetsSubmarines"))
put([49],B+"facilityCapacity;"+C+"Catalog::productionCapacity",T("economy","productionRepair")+";"+T("catalog","technologyAndConstruction"))
put([50],B+"EconomyRules::apply;"+A+"applyFacilityBombDamage",T("economy","upgradesDiscountsAndCaps")+";"+T("air_tests","improvedConstructionPerPlayerTurn"))
put([51,69,87],A+"AirRules::apply;"+L+"beginLandBattle",T("air_integration","actualAirborneEntryResolvesFightersAndAaaBeforeLanding")+";"+T("air_integration","survivingAirborneTransportLandsBeforeInfantryAttack")+";"+T("land_combat","airborneFightersAndBothAaaRollTogether")+";"+T("catalog","technologyAndConstruction"))
put([52,97],O+"applyNavalOperationAction;"+L+"beginLandBattle",T("naval_operations","waitingArmorRemainsAboardUntilFoothold")+";"+T("naval_operations","amphibiousDoubleCasualtiesAndExemptions")+";"+T("naval_operations","sharedShoreCasualtiesNeedBothPolicies"))
put([53],C+"Catalog::stats;"+A+"validateFlight",T("catalog","modesAndConditionalStats")+";"+T("air_tests","flightPermissionAndRange"))
put([54],N+"applyNavalCombatChance",T("naval_combat","mapPairingAndAdvancedSubmarineImmunity")+";"+T("catalog","modesAndConditionalStats"))
put([55],C+"Catalog::purchaseEligibility;"+N+"applyNavalCombatAction;"+A+"airLandingPlanAvailable",T("catalog","navalDamage")+";"+T("air_logistics","jointLandingUsesWeightedCarrierAssignments")+";"+T("naval_combat","capitalHitsAndDamageValues"))
put([56],M+"validateRoute;"+M+"validateFactoryRailRoute;"+V+"strategicNavalCapacity",T("movement","factoryRelocation")+";"+T("movement","railGaugeDamageCapacity")+";"+T("naval_movement","strategicCapacityEndpointsAndUnloading"))
put([57],A+"AirRules::apply;"+A+"AirRules::applyChance;"+L+"landCombatStats",T("air_mission","rocketRangeIgnoresAircraftInterceptionAndRequiresNoTransport")+";"+T("air_tests","bombingDamageThenAAAndReplay")+";"+T("catalog","purchaseBoundariesAndForeignExclusion"))
put([58],B+"EconomyRules::actions;"+B+"EconomyRules::apply",T("economy","stagedQueues")+";"+T("economy","productionRepair")+";"+T("catalog","purchaseBoundariesAndForeignExclusion"))
put([59],B+"damageConstruction;"+P+"captureLand",T("economy","constructionAndCapture"))
put([60],B+"EconomyRules::apply;"+B+"finishEconomyPlacement",T("economy","replacementUpgradeAndEliteLease")+";"+T("economy","upgradesDiscountsAndCaps"))
put([61,110],B+"EconomyRules::apply;"+B+"finishEconomyPlacement",T("economy","cityAndRailRepair")+";"+T("economy","productionRepair")+";"+T("economy","replacementUpgradeAndEliteLease"))
put([62],B+"EconomyRules::apply;"+B+"finishEconomyPlacement",T("economy","sharedShipyardRepair")+";"+T("naval_operations","berthLocksMovementAndKeepsCargo")+";"+T("campaign_env","repairsRailAndNeutralAttribution"))
put([63,111],"src/economy_lendlease.cpp::lendLeasePermitted;src/economy_lendlease.cpp::lendLeaseActions;"+M+"lendLeaseSupplyRoute",T("economy","ladaoLease")+";"+T("economy","leaseCredits")+";"+T("economy","replacementUpgradeAndEliteLease")+";"+T("movement","lendLeaseDestinationException"))
put([65,70],V+"navalMovementActions;"+V+"applyNavalMovementAction",T("naval_movement","peacefulSeaEntryWindowsAreSequentialAndReplayable")+";"+T("naval_movement","defenderDeclarationQueuesCombatAndAllowsReinforcements")+";"+T("naval_movement","immediateSubmarineReactionResumesTheVoyage"))
put([66,101],M+"validateRoute",T("movement","hostileStopsAndOrigins")+";"+T("movement","immobileRailAndContinuousPossession"))
put([67],A+"validateFlight;"+A+"airLandingPlanAvailable;"+V+"applyNavalMovementAction",T("air_logistics","attackDeclarationsRequireACombinedReturnPlan")+";"+T("air_logistics","jointLandingCannotCountTheSameCarrierSlotsTwice")+";"+T("naval_movement","carrierMovementGivesNoAircraftRide"))
put([68],A+"AirRules::actions;"+V+"applyNavalMovementAction;"+N+"beginNavalBattle",T("air_logistics","endPatrolOnlyNoncombat")+";"+T("air_mission","immediatePatrolLandingLoss")+";"+T("naval_movement","defendingCarrierAircraftMayEngageMovingSubmarine"))
put([71],V+"validateNavalRoute",T("naval_movement","supplyDamageAndSubmarineRanges"))
put([72],V+"applyNavalMovementAction;"+A+"finishAirCombat",T("air_integration","successfulAirScreeningContinuesToAnotherAttackAndReplays")+";"+T("air_integration","failedAirScreeningForcesTheContinuingAircraftToLand")+";"+T("air_integration","continuingAircraftCannotPerformAnAirborneAssault")+";"+T("naval_operations","seaMustBeClearedBeforeAssault"))
put([73],V+"applyNavalMovementAction;"+O+"applyNavalOperationAction",T("naval_movement","loadVoyageAndFriendlyUnload")+";"+T("naval_movement","movedCargoAndSplitUnloadingRejected")+";"+T("naval_combat","transportsLastAndLinkedCargo"))
put([74],V+"applyNavalMovementChance;"+N+"applyNavalCombatChance",T("naval_movement","attackingRaiderSlipIsExplicitAndReplayable")+";"+T("naval_combat","raiderDiscoveryTiesAndSlipStayInSea"))
put([76],M+"seaBlockaded;"+M+"facilityBlockaded",T("movement","blockadeSurfaceOnly")+";"+T("movement","seaRangeRefreshAndSharedPorts")+";"+T("naval_movement","blockadedPortKeepsContinuingShipsInBerth"))
put([77,82],L+"LandCombatRules::actions;"+L+"beginLandBattle;"+A+"beginAirDefence",T("land_combat","simultaneousFireAndReplay")+";"+T("land_combat","replayableGroundCampaignAndCounterattack")+";"+T("air_mission","scrambleReturnAtPhaseEnd"))
put([78],L+"LandCombatRules::applyChance;"+N+"applyNavalCombatChance",T("land_combat","firstStrikePreventsOrdinaryReturn")+";"+T("land_combat","opposingFirstStrikesAreSimultaneous")+";"+T("land_combat","targetSelectionAndFallback")+";"+T("naval_combat","reciprocalHitsAndReplay"))
put([79,119],L+"LandCombatRules::applyChance",T("land_combat","aaaFiresOnlyOnceAndCountsAircraft")+";"+T("land_combat","airborneFightersAndBothAaaRollTogether")+";"+T("naval_operations","amphibiousDoubleCasualtiesAndExemptions"))
put([80],L+"landRetreatOrigins;"+N+"applyNavalCombatAction",T("land_combat","onlyLandEntriesCreateRetreatDestinations")+";"+T("land_truce","ordinarySharedRetreatHasNoEntryOrigin")+";"+T("naval_combat","retreatUsesActualShipEntry"))
put([81],A+"beginAirDefence",T("air_mission","scrambleReturnAtPhaseEnd")+";"+T("air_logistics","scrambledAircraftReserveTheirOriginalCarrierSeats")+";"+T("naval_combat","shipScrambleAndSkeletonCrewExclusion"))
put([83],L+"blitzEligible;"+M+"blitzPairValid",T("land_combat","blitzPairingIsAnExplicitChoice")+";"+T("movement","pairedBlitz")+";"+T("air_mission","pairedAircraftBlitz"))
put([85],L+"registerAttritionBattle;"+A+"AirRules::apply",T("land_combat","attritionIsSeparateAndNoReturnFire")+";"+T("air_mission","artilleryCityBombingRequiresAnUnmovedStartingNeighbor"))
put([86],N+"applyNavalCombatChance;"+L+"beginLandBattle",T("naval_combat","seaplaneAswBonusTargetsSubmarines")+";"+T("air_tests","airliftHeavyCapacityAndContinuation"))
put([88,91],A+"beginAirDefence;"+A+"AirRules::applyChance",T("air_tests","bombingDamageThenAAAndReplay")+";"+T("air_tests","interceptorAndEscortSimultaneous")+";"+T("air_mission","rocketRadarBeforeDamage"))
put([89],A+"AirRules::applyChance",T("air_tests","cityPermanentIPPAndDestruction")+";"+T("air_mission","destroyedCityTechnologyChoice"))
put([90],A+"AirRules::applyChance",T("air_tests","railroadSideAndAllTracks"))
put([92],O+"applyNavalOperationAction;"+N+"applyNavalCombatChance",T("naval_combat","portAttackStillGetsFacilityAaAfterShipLoss")+";"+T("naval_operations","actualNavalAirDeclarationsKeepContextAndCombatPhase"))
put([93],A+"AirRules::apply;"+A+"returnCarpetBombers;"+L+"LandCombatRules::applyChance",T("campaign_integration","carpetBombingParticipatesOnceAndCannotBeHitByInfantry"))
put([94],N+"applyNavalCombatChance",T("naval_combat","submarineFirstStrikeAndDestroyer")+";"+T("naval_combat","protectedSubmarinesAndSubmerge")+";"+T("naval_combat","transportsLastAndLinkedCargo"))
put([95],N+"applyNavalCombatAction",T("naval_combat","carrierLossRescuesDefendingAircraft"))
put([96],O+"applyNavalOperationAction;"+L+"beginLandBattle",T("naval_operations","seaMustBeClearedBeforeAssault")+";"+T("naval_operations","shoreBombardmentAndCoastalFirstStrike")+";"+T("naval_operations","adjacentLandAndAmphibiousAttacksResolveTogether"))
put([99],L+"LandCombatRules::applyChance;"+P+"captureLand;"+A+"airLandingSpots",T("air_tests","noAircraftCapture")+";"+T("politics","mandatoryLiberationAndProvenWithdrawal")+";"+T("land_truce","japaneseCaptureGiftCanEndAnExistingTruce")+";"+T("movement","giftWithdrawalRequiresExecutableSharedLoading")+";"+T("movement","pendingGiftsShareTheSameTransportCapacity"))
put([100],P+"captureLand",T("politics","captureCapitalAndFacilities"))
put([102],M+"validateRoute",T("movement","railGaugeDamageCapacity")+";"+T("movement","riverBanksAndImpassableRoads")+";"+T("movement","immobileRailAndContinuousPossession"))
put([103],A+"AirRules::apply;"+A+"validateFlight",T("air_tests","airliftHeavyCapacityAndContinuation")+";"+T("air_logistics","jointLandingUsesWeightedCarrierAssignments")+";"+T("naval_movement","carrierMovementGivesNoAircraftRide"))
put([104],V+"validateNavalRoute;"+V+"applyNavalMovementAction",T("naval_movement","strategicAndNoncombatBlockers")+";"+T("naval_movement","movedCargoAndSplitUnloadingRejected"))
put([105],V+"validateNavalRoute;"+V+"strategicNavalCapacity",T("naval_movement","strategicCapacityEndpointsAndUnloading")+";"+T("naval_movement","strategicPickupAlongRoute"))
put([106],O+"queueDamagedPortEvacuation;"+O+"applyNavalOperationAction",T("naval_operations","berthLocksMovementAndKeepsCargo")+";"+T("naval_operations","damagedPortEvacuationSuspendsAndResumesBombing")+";"+T("naval_operations","thirdPartyEvacuationUsesFleetRolesAndPreservesBombing")+";"+T("naval_movement","portExitCostsZero"))
put([107],O+"preparePortLandDefence",T("naval_operations","temporaryCrewAndSkeletonRestriction"))
put([108],B+"facilityCapacity;"+B+"EconomyRules::apply",T("economy","productionRepair")+";"+T("economy","stagedQueues"))
put([109],B+"EconomyRules::apply",T("economy","decentralizedAndMilitia")+";"+T("politics_influence","recruitmentMilitiaExemptFromPurchaseQuota"))
put([113],O+"resolveCapturedPorts;"+O+"applyNavalOperationChance",T("naval_operations","capturedShipRollPreservesDamage"))
put([114],F+"influenceActions;"+F+"applyInfluenceChance",T("politics_influence","mongoliaRecruitmentIsIndependent")+";"+T("politics_influence","offshoreThresholdDoesNotForbidPlacement")+";"+T("politics_influence","freeShipAdvanceAndFacilityRepair"))
put([115],B+"evaluateIncome;"+B+"EconomyRules::finishTurn;"+R+"Engine::endPhase",T("economy","income")+";"+T("economy","accountingReplay")+";"+T("campaign_env","setupValuesAndNoDoubleCounting"))
put([116],L+"landCombatStats;"+C+"Catalog::purchaseEligibility",T("land_combat","terrainAndJapaneseModifiers")+";"+T("land_combat","artilleryPairingAndSurvivorRecalculation")+";"+T("catalog","purchaseBoundariesAndForeignExclusion"))
put([117],M+"validateRoute;"+L+"landCombatStats",T("movement","pairedTowingMovesWithoutChangingCatalogStats")+";"+T("movement","combatTowingRegistersBothApproachesAndReplays")+";"+T("land_combat","targetSelectionAndFallback")+";"+T("catalog","purchaseBoundariesAndForeignExclusion"))
put([118],L+"landCombatStats",T("land_combat","artilleryPairingAndSurvivorRecalculation"))
put([120],A+"AirRules::actions;"+N+"applyNavalCombatChance;"+L+"landCombatStats",T("air_tests","interceptorAndEscortSimultaneous")+";"+T("naval_combat","seaplaneAswBonusTargetsSubmarines")+";"+T("land_combat","targetSelectionAndFallback"))
put([121],V+"validateNavalRoute;"+N+"applyNavalCombatChance;"+A+"airLandingPlanAvailable",T("naval_combat","capitalHitsAndDamageValues")+";"+T("naval_movement","supplyDamageAndSubmarineRanges")+";"+T("air_logistics","jointLandingUsesWeightedCarrierAssignments")+";"+T("catalog","navalDamage"))
put([122],A+"AirRules::apply;"+L+"beginLandBattle",T("land_combat","unsupportedRocketsFallOnEnemyLandEntry")+";"+T("land_combat","strategicRocketsAreNotCombatCasualties")+";"+T("air_mission","rocketRangeIgnoresAircraftInterceptionAndRequiresNoTransport"))
put([123,126],B+"facilityCapacity;"+M+"navalFacilityUsable",T("economy","sharedShipyardRepair")+";"+T("movement","seaRangeRefreshAndSharedPorts")+";"+T("campaign_setup","main"))
put([124],P+"captureLand;"+B+"facilityCapacity",T("politics","captureCapitalAndFacilities")+";"+T("economy","constructionAndCapture")+";"+T("economy","productionRepair"))
put([125],A+"beginAirDefence;"+A+"validateFlight;"+M+"navalFacilityUsable",T("air_logistics","baseMovementNeedsSupplyAndAge")+";"+T("air_mission","scrambleReturnAtPhaseEnd")+";"+T("catalog","technologyAndConstruction"))
put([128],O+"applyNavalOperationChance",T("naval_operations","shoreBombardmentAndCoastalFirstStrike"))
put([129],B+"EconomyRules::apply;"+M+"railUndamaged",T("economy","foreignRailConsent")+";"+T("economy","cityAndRailRepair")+";"+T("movement","railGaugeDamageCapacity"))
put([131],P+"recordLandAttack;"+P+"refreshPoliticalState",T("politics","ccpNoUnitsIsNotSurrenderOrGameEnd")+";"+T("politics_warlords","dadaoAlignment"))
put([132],P+"refreshPoliticalState",T("politics","immediateEvolutionOutsideOwnTurn")+";"+T("politics","ownTurnEvolutionExceptionAndOptionalFactory")+";"+T("politics","ccpEvolutionLosesMinorActionsImmediately")+";"+T("land_truce","japaneseCaptureGiftCanEndAnExistingTruce"))
put([133,136],F+"influenceActions;"+F+"applyInfluenceAction;"+F+"applyInfluenceChance",T("politics_influence","wholeWarlordAndUniqueAdjacency")+";"+T("politics_influence","spendingCapAndPaidBeforeChance")+";"+T("politics_influence","failedInfluenceAndNaturalTwelve")+";"+T("politics_influence","dadaoRemainsControlledMinorAndJoins")+";"+T("politics_influence","ccpRecruitmentAndSplitMilitia"))
put([137],P+"declareWar;"+L+"landCombatStats;"+A+"beginAirDefence",T("air_mission","selectedSurpriseBombingUsesFirstStrikeWithoutRemovingFacilityAA")+";"+T("politics","declarationGatesAndUnknownAccounting")+";"+T("land_combat","terrainAndJapaneseModifiers"))
put([138],V+"navalCargoFits;"+L+"landCombatStats",T("naval_movement","destroyerTransportRangeAndStop")+";"+T("land_combat","terrainAndJapaneseModifiers"))
put([140],L+"LandCombatRules::applyChance;"+B+"EconomyRules::apply",T("land_combat","kmtLowMoraleEmptyAndOrigins")+";"+T("land_combat","lowMoraleUnitsCannotBeCasualties")+";"+T("land_truce","voluntaryKmtBreakUsesTheAttackingDiceInEveryRound")+";"+T("economy","decentralizedAndMilitia"))

INACTIVE_EXTRA = {
    "R064": "No eligible neutral Minor Power can arise in the frozen participant set: Chinese warlords are ineligible for ordinary diplomacy; Mongolia and Dadao are controlled minors; KMT/CCP have separate Chinese rules. No ordinary diplomacy roll handler is asserted here. Anti-diplomacy in R056 is likewise inactive.",
}

def reference(spec, fixture=False):
    file, symbol = spec.split("::", 1)
    content = (ROOT/file).read_text()
    pattern = r"\b" + re.escape(symbol) + r"\s*\("
    definition_pattern=r"^[\w:<>, &*]+\b"+re.escape(symbol)+r"\s*\([^;{}]*\)\s*(?:const\s*)?\{"
    match = re.search(definition_pattern, content, re.MULTILINE)
    if not match:
        raise ValueError(f"Missing {'fixture' if fixture else 'handler'} {spec}")
    if fixture and symbol != "main":
        main = content[content.index("int main("):]
        if not re.search(r"\b"+re.escape(symbol)+r"\b", main):
            raise ValueError(f"Fixture is not invoked by executable main: {spec}")
    result={"file": file, "symbol": symbol, "line": content.count("\n", 0, match.start())+1}
    if fixture:
        definition=re.search(r"\b(?:void|int)\s+"+re.escape(symbol)+r"\s*\([^)]*\)\s*\{",content)
        if not definition: raise ValueError(f"Fixture has no definition: {spec}")
        start=definition.end();depth=1;quoted=False;escaped=False;end=start
        for end in range(start,len(content)):
            char=content[end]
            if quoted:
                if escaped: escaped=False
                elif char=="\\": escaped=True
                elif char=='"': quoted=False
            elif char=='"': quoted=True
            elif char=="{": depth+=1
            elif char=="}":
                depth-=1
                if depth==0: break
        body=content[start:end]
        # Fixture assertion messages are durable readable behavior claims. Keep
        # all messages rather than quietly selecting a flattering subset.
        messages=[]
        for call in re.finditer(r"(?<![\w.>])(?:check|require|rejects)\s*\(",body):
            stack=["("];quoted=False;escaped=False;last=call.end()
            for cursor in range(call.end(),len(body)):
                char=body[cursor]
                if quoted:
                    if escaped: escaped=False
                    elif char=="\\": escaped=True
                    elif char=='"': quoted=False
                elif char=='"': quoted=True
                elif char in "([{": stack.append(char)
                elif char in ")]}":
                    stack.pop()
                    if not stack: break
                elif char=="," and len(stack)==1: last=cursor+1
            diagnostic=" ".join(re.findall(r'"((?:[^"\\]|\\.)*)"',body[last:cursor]))
            if diagnostic and diagnostic not in messages: messages.append(diagnostic)
        result["behavior_assertions"]=messages
        if not messages: raise ValueError(f"No readable behavior assertion in {spec}")
    return result

def build():
    rows=[]
    for line in LEDGER.read_text().splitlines():
        if not re.match(r"\| R\d{3};", line): continue
        columns=[x.strip() for x in line.split("|")[1:-1]]
        row_id, source = columns[0].split(";",1)
        item={"id":row_id,"source":source.strip(),"contract":columns[1],"m0_acceptance":columns[-1]}
        inactive=columns[1].startswith("I:") or row_id in INACTIVE_EXTRA
        if inactive:
            item.update(status="inactive_in_frozen_profile",reason=INACTIVE_EXTRA.get(row_id,columns[1][3:]))
            item["profile_evidence"]=["game_content/scenarios/japan_china_1936/m0/scenario_contract.json","game_content/scenarios/japan_china_1936/manifest.json","tests/campaign_setup_tests.cpp"]
        else:
            if row_id not in E: raise ValueError(f"Unmapped active contract {row_id}")
            item.update(status="replaced_by_approved_campaign_policy" if columns[1].startswith("O:") else "runtime_and_executable_evidence_indexed")
            item["handlers"]=[reference(x) for x in E[row_id]["handlers"]]
            item["fixtures"]=[reference(x,True) for x in E[row_id]["fixtures"]]
        rows.append(item)
    assert [r["id"] for r in rows] == [f"R{i:03}" for i in range(143)]
    files=sorted({ref["file"] for row in rows for key in ("handlers","fixtures") for ref in row.get(key,[])})
    return {"schema_version":1,"scope":"Evidence index for all stable campaign rule acceptance rows (R000–R142). A listed focused fixture exercises the named mechanic; it is not a claim that every clause or legal position has exhaustive coverage. Full initial-state campaign traces are separately recorded.","m0_ledger_sha256":hashlib.sha256(LEDGER.read_bytes()).hexdigest(),"evidence_file_sha256":{file:hashlib.sha256((ROOT/file).read_bytes()).hexdigest() for file in files},"rows":rows}

def render_markdown(data):
    counts={status:sum(x["status"]==status for x in data["rows"]) for status in sorted({x["status"] for x in data["rows"]})}
    lines=["# Campaign runtime coverage","",data["scope"],"",f"All 143 stable rule IDs are indexed: {counts}.","","Ordinary diplomacy (R064) and the anti-diplomacy facet of R056 have no eligible neutral target in this profile. Their ordinary diplomacy-roll implementation is not represented as complete.","","Generated by `python3 tools/build_campaign_coverage.py` from the [rules ledger](rules-ledger.md). This checks named handlers, fixture definitions and invocation from their executable's `main`; it does not execute those fixtures. Test-run results and complete trace provenance are recorded separately.","","| Rule ID | Evidence | Runtime entry points and executable fixtures / inactive reason |","| --- | --- | --- |"]
    for row in data["rows"]:
        if row["status"]=="inactive_in_frozen_profile": detail=row["reason"]
        else:
            refs=row["handlers"]+row["fixtures"]
            detail="; ".join(f"[{x['symbol']}]({Path(os.path.relpath(ROOT/x['file'], OUT)).as_posix()}#L{x['line']})" for x in refs)
        lines.append(f"| {row['id']} | {row['status']} | {detail.replace('|','/')} |")
    return "\n".join(lines)+"\n", counts


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--check",action="store_true");args=parser.parse_args()
    data=build()
    markdown, counts = render_markdown(data)
    if args.check:
        saved=json.loads(JSON_OUTPUT.read_text())
        if saved!=data or MARKDOWN_OUTPUT.read_text()!=markdown:
            raise SystemExit("Coverage index is stale; regenerate after reviewing changed handlers/fixtures")
        print("All 143 rule rows, named handlers, executable fixture assertions, evidence hashes and Markdown match")
        raise SystemExit(0)
    OUT.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(data,indent=2)+"\n")
    MARKDOWN_OUTPUT.write_text(markdown)
    print(json.dumps(counts))
