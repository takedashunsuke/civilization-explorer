from __future__ import annotations

import math
import random
from collections import defaultdict

from simulation.models import (
    ActionType,
    AgentState,
    Allegiance,
    ChosenAction,
    EventRecord,
    HistoryRecord,
    InstitutionState,
    MetricsSnapshot,
    Personality,
    Position,
    RelationshipState,
    SettlementState,
    SimulationState,
    WorldParams,
    WorldState,
)


SETTLEMENT_DISTANCE = 18.0
ENERGY_WAIT_THRESHOLD = 0.15
MAX_MEMORY = 10
ACTION_PRIORITY = {
    ActionType.resist: 0,
    ActionType.obey: 0,
    ActionType.conflict: 1,
    ActionType.cooperate: 2,
    ActionType.migrate: 3,
    ActionType.wait: 4,
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def pair_key(a_id: str, b_id: str) -> tuple[str, str]:
    return (a_id, b_id) if a_id < b_id else (b_id, a_id)


def create_simulation(sim_id: str, params: WorldParams) -> SimulationState:
    rng = random.Random(params.seed)
    agents: list[AgentState] = []
    for i in range(params.population):
        coop = clamp(params.initial_values.cooperation + rng.uniform(-0.2, 0.2))
        aggr = clamp(0.4 + rng.uniform(-0.25, 0.25))
        ambi = clamp(0.4 + rng.uniform(-0.25, 0.25))
        agents.append(
            AgentState(
                id=f"agent_{i}",
                name=f"A{i}",
                position=Position(x=rng.uniform(5, 95), y=rng.uniform(5, 95)),
                wealth=rng.uniform(8, 20),
                energy=clamp(0.7 + rng.uniform(-0.2, 0.2)),
                happiness=clamp(0.5 + rng.uniform(-0.15, 0.15)),
                personality=Personality(cooperation=coop, aggression=aggr, ambition=ambi),
                goal="survive and grow",
            )
        )

    relationships: list[RelationshipState] = []
    for i, a in enumerate(agents):
        for b in agents[i + 1 :]:
            relationships.append(
                RelationshipState(
                    a_id=a.id,
                    b_id=b.id,
                    trust=rng.uniform(-0.1, 0.2),
                    affinity=rng.uniform(-0.05, 0.15),
                )
            )

    world = WorldState(
        turn=0,
        seed=params.seed,
        population_cap=params.population,
        resource_pool=params.resource_pool,
        education_level=params.education_level,
        tax_rate=params.tax_rate,
        institution=params.institution,
        initial_values=params.initial_values,
        institution_runtime=InstitutionState(
            authority=0.4 + 0.3 * params.initial_values.authority_acceptance
        ),
    )

    sim = SimulationState(
        id=sim_id,
        world=world,
        agents=agents,
        relationships=relationships,
        settlements=[],
    )
    recompute_settlements(sim)
    sim.last_metrics = compute_metrics(sim, cooperate_successes=0, action_count=0)
    return sim


def get_relationship(sim: SimulationState, a_id: str, b_id: str) -> RelationshipState:
    key = pair_key(a_id, b_id)
    for rel in sim.relationships:
        if pair_key(rel.a_id, rel.b_id) == key:
            return rel
    rel = RelationshipState(a_id=key[0], b_id=key[1])
    sim.relationships.append(rel)
    return rel


def distance(a: Position, b: Position) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def nearest_other(sim: SimulationState, agent: AgentState) -> AgentState | None:
    others = [a for a in sim.agents if a.alive and a.id != agent.id]
    if not others:
        return None
    return min(others, key=lambda o: distance(agent.position, o.position))


def heuristic_decide(sim: SimulationState, agent: AgentState, rng: random.Random) -> ChosenAction:
    if agent.energy < ENERGY_WAIT_THRESHOLD:
        return ChosenAction(agent_id=agent.id, action=ActionType.wait, reason="low energy")

    target = nearest_other(sim, agent)
    p = agent.personality
    roll = rng.random()

    if target is not None:
        rel = get_relationship(sim, agent.id, target.id)
        if p.aggression > 0.65 and rel.trust < 0 and roll < 0.35:
            return ChosenAction(
                agent_id=agent.id,
                action=ActionType.conflict,
                target_id=target.id,
                reason="aggressive heuristic",
            )
        if p.cooperation > 0.45 and roll < 0.45 + 0.2 * rel.trust:
            return ChosenAction(
                agent_id=agent.id,
                action=ActionType.cooperate,
                target_id=target.id,
                reason="cooperative heuristic",
            )

    if sim.world.institution.value != "anarchy":
        if p.ambition < 0.4 and roll < 0.25 + sim.world.initial_values.authority_acceptance * 0.2:
            return ChosenAction(agent_id=agent.id, action=ActionType.obey, reason="obey institution")
        if p.ambition > 0.7 and roll < 0.2:
            return ChosenAction(agent_id=agent.id, action=ActionType.resist, reason="resist institution")

    if p.ambition > 0.55 and roll < 0.25:
        dx = rng.uniform(-12, 12)
        dy = rng.uniform(-12, 12)
        return ChosenAction(
            agent_id=agent.id,
            action=ActionType.migrate,
            reason=f"migrate:{agent.position.x + dx:.1f},{agent.position.y + dy:.1f}",
        )

    return ChosenAction(agent_id=agent.id, action=ActionType.wait, reason="default wait")


def decide_actions(sim: SimulationState, rng: random.Random) -> list[ChosenAction]:
    # Phase 2 で LLM に差し替え。現状は常にヒューリスティック。
    return [heuristic_decide(sim, agent, rng) for agent in sim.agents if agent.alive]


def resolve_actions(sim: SimulationState, choices: list[ChosenAction], rng: random.Random) -> tuple[int, int]:
    agents = {a.id: a for a in sim.agents}
    events: list[EventRecord] = []
    cooperate_successes = 0

    # conflict が同一ペアで出たら cooperate を無効化
    conflict_pairs: set[tuple[str, str]] = set()
    for c in choices:
        if c.action == ActionType.conflict and c.target_id:
            conflict_pairs.add(pair_key(c.agent_id, c.target_id))

    normalized: list[ChosenAction] = []
    for c in choices:
        if (
            c.action == ActionType.cooperate
            and c.target_id
            and pair_key(c.agent_id, c.target_id) in conflict_pairs
        ):
            normalized.append(
                ChosenAction(agent_id=c.agent_id, action=ActionType.wait, reason="conflict overrides cooperate")
            )
        else:
            normalized.append(c)

    normalized.sort(key=lambda c: (ACTION_PRIORITY[c.action], c.agent_id))

    for choice in normalized:
        actor = agents.get(choice.agent_id)
        if actor is None or not actor.alive:
            continue

        action = choice.action
        if actor.energy < ENERGY_WAIT_THRESHOLD and action != ActionType.wait:
            action = ActionType.wait

        if action == ActionType.wait:
            before = actor.energy
            actor.energy = clamp(actor.energy + 0.1)
            events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=actor.id,
                    action=ActionType.wait,
                    detail=choice.reason or "wait",
                    deltas={"energy": actor.energy - before},
                )
            )
            continue

        if action == ActionType.cooperate:
            target = agents.get(choice.target_id or "")
            if target is None or not target.alive:
                actor.energy = clamp(actor.energy + 0.05)
                events.append(
                    EventRecord(
                        turn=sim.world.turn,
                        actor_id=actor.id,
                        action=ActionType.wait,
                        detail="cooperate fallback: missing target",
                    )
                )
                continue

            rel = get_relationship(sim, actor.id, target.id)
            max_wealth = max(a.wealth for a in sim.agents) or 1.0
            p = clamp(
                0.5
                + 0.25 * rel.trust
                + 0.20 * sim.world.education_level
                + 0.15 * ((actor.personality.cooperation + target.personality.cooperation) / 2)
                - 0.10 * abs(actor.wealth - target.wealth) / max_wealth
            )
            success = rng.random() < p
            if success:
                gain = min(3.0, sim.world.resource_pool * 0.02 + 1.0)
                sim.world.resource_pool = max(0.0, sim.world.resource_pool - gain * 2)
                actor.wealth += gain
                target.wealth += gain
                rel.trust = clamp(rel.trust + 0.1, -1, 1)
                rel.affinity = clamp(rel.affinity + 0.05, -1, 1)
                actor.happiness = clamp(actor.happiness + 0.05)
                target.happiness = clamp(target.happiness + 0.05)
                cooperate_successes += 1
                detail = f"cooperate success with {target.id}"
            else:
                actor.energy = clamp(actor.energy - 0.1)
                target.energy = clamp(target.energy - 0.1)
                rel.trust = clamp(rel.trust - 0.05, -1, 1)
                detail = f"cooperate failed with {target.id}"
            events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=actor.id,
                    action=ActionType.cooperate,
                    target_id=target.id,
                    success=success,
                    detail=detail,
                )
            )
            _remember(actor, detail)
            _remember(target, detail)
            continue

        if action == ActionType.conflict:
            target = agents.get(choice.target_id or "")
            if target is None or not target.alive:
                events.append(
                    EventRecord(
                        turn=sim.world.turn,
                        actor_id=actor.id,
                        action=ActionType.wait,
                        detail="conflict fallback: missing target",
                    )
                )
                continue

            def power(x: AgentState) -> float:
                return x.wealth * 0.4 + x.energy * 0.3 + x.personality.aggression * 0.3 + rng.random() * 0.2

            actor_power = power(actor)
            target_power = power(target)
            winner, loser = (actor, target) if actor_power >= target_power else (target, actor)
            stolen = min(4.0, loser.wealth * 0.2)
            winner.wealth += stolen
            loser.wealth = max(0.0, loser.wealth - stolen)
            winner.energy = clamp(winner.energy - 0.15)
            loser.energy = clamp(loser.energy - 0.2)
            loser.happiness = clamp(loser.happiness - 0.1)
            rel = get_relationship(sim, actor.id, target.id)
            rel.trust = clamp(rel.trust - 0.2, -1, 1)
            detail = f"conflict: {winner.id} beat {loser.id}"
            events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=actor.id,
                    action=ActionType.conflict,
                    target_id=target.id,
                    success=winner.id == actor.id,
                    detail=detail,
                    deltas={"stolen": stolen},
                )
            )
            _remember(actor, detail)
            _remember(target, detail)
            continue

        if action == ActionType.migrate:
            # reason に migrate:x,y があれば使う。なければランダム近傍。
            nx, ny = actor.position.x, actor.position.y
            if choice.reason.startswith("migrate:"):
                try:
                    coords = choice.reason.split(":", 1)[1]
                    nx_s, ny_s = coords.split(",")
                    nx, ny = float(nx_s), float(ny_s)
                except ValueError:
                    nx += rng.uniform(-10, 10)
                    ny += rng.uniform(-10, 10)
            else:
                nx += rng.uniform(-10, 10)
                ny += rng.uniform(-10, 10)
            actor.position = Position(x=clamp(nx, 0, 100), y=clamp(ny, 0, 100))
            actor.energy = clamp(actor.energy - 0.2)
            detail = f"migrated to ({actor.position.x:.1f},{actor.position.y:.1f})"
            events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=actor.id,
                    action=ActionType.migrate,
                    detail=detail,
                )
            )
            _remember(actor, detail)
            continue

        if action == ActionType.obey:
            pay = actor.wealth * sim.world.tax_rate
            actor.wealth = max(0.0, actor.wealth - pay)
            sim.world.institution_runtime.treasury += pay
            actor.allegiance = Allegiance.obey
            sim.world.institution_runtime.authority = clamp(
                sim.world.institution_runtime.authority + 0.02
            )
            if sim.world.tax_rate > 0.2:
                actor.happiness = clamp(actor.happiness - 0.02)
            detail = f"obeyed, paid {pay:.2f}"
            events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=actor.id,
                    action=ActionType.obey,
                    detail=detail,
                    deltas={"tax": pay},
                )
            )
            _remember(actor, detail)
            continue

        if action == ActionType.resist:
            actor.allegiance = Allegiance.resist
            sim.world.institution_runtime.authority = clamp(
                sim.world.institution_runtime.authority - 0.03
            )
            resist_count = sum(1 for a in sim.agents if a.alive and a.allegiance == Allegiance.resist)
            if resist_count >= max(2, len([a for a in sim.agents if a.alive]) // 3):
                actor.happiness = clamp(actor.happiness + 0.02)
            else:
                actor.happiness = clamp(actor.happiness - 0.05)
            detail = "resisted institution"
            events.append(
                EventRecord(
                    turn=sim.world.turn,
                    actor_id=actor.id,
                    action=ActionType.resist,
                    detail=detail,
                )
            )
            _remember(actor, detail)

    sim.events.extend(events)
    return cooperate_successes, len(normalized)


def _remember(agent: AgentState, text: str) -> None:
    agent.memory.append(text)
    if len(agent.memory) > MAX_MEMORY:
        agent.memory = agent.memory[-MAX_MEMORY:]


def recompute_settlements(sim: SimulationState) -> None:
    alive = [a for a in sim.agents if a.alive]
    parent = {a.id: a.id for a in alive}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i, a in enumerate(alive):
        for b in alive[i + 1 :]:
            if distance(a.position, b.position) <= SETTLEMENT_DISTANCE:
                union(a.id, b.id)

    groups: dict[str, list[AgentState]] = defaultdict(list)
    for a in alive:
        groups[find(a.id)].append(a)

    settlements: list[SettlementState] = []
    for idx, members in enumerate(groups.values()):
        cx = sum(m.position.x for m in members) / len(members)
        cy = sum(m.position.y for m in members) / len(members)
        sid = f"settlement_{idx}"
        for m in members:
            m.settlement_id = sid
        settlements.append(
            SettlementState(
                id=sid,
                position=Position(x=cx, y=cy),
                member_ids=[m.id for m in members],
                shared_wealth=sum(m.wealth for m in members) * 0.05,
            )
        )
    sim.settlements = settlements


def compute_metrics(sim: SimulationState, cooperate_successes: int, action_count: int) -> MetricsSnapshot:
    alive = [a for a in sim.agents if a.alive]
    wealths = [a.wealth for a in alive] or [0.0]
    mean_w = sum(wealths) / len(wealths)
    var = sum((w - mean_w) ** 2 for w in wealths) / len(wealths)
    inequality = math.sqrt(var) / (mean_w + 1e-6)
    trusts = [r.trust for r in sim.relationships] or [0.0]
    mean_trust = sum(trusts) / len(trusts)
    coop_rate = (cooperate_successes / action_count) if action_count else 0.0
    mean_happiness = sum(a.happiness for a in alive) / len(alive) if alive else 0.0
    return MetricsSnapshot(
        inequality=round(inequality, 4),
        mean_trust=round(mean_trust, 4),
        cooperation_rate=round(coop_rate, 4),
        authority=round(sim.world.institution_runtime.authority, 4),
        mean_happiness=round(mean_happiness, 4),
    )


def end_of_turn(sim: SimulationState, cooperate_successes: int, action_count: int) -> None:
    recompute_settlements(sim)
    sim.world.resource_pool += 2.0 + 3.0 * sim.world.education_level
    sim.world.institution_runtime.authority = clamp(sim.world.institution_runtime.authority)
    metrics = compute_metrics(sim, cooperate_successes, action_count)
    sim.last_metrics = metrics
    sim.history.append(
        HistoryRecord(
            turn=sim.world.turn,
            summary=(
                f"t={sim.world.turn} agents={sum(1 for a in sim.agents if a.alive)} "
                f"ineq={metrics.inequality:.2f} trust={metrics.mean_trust:.2f} "
                f"coop={metrics.cooperation_rate:.2f}"
            ),
            metrics=metrics,
        )
    )
    sim.world.turn += 1


def tick(sim: SimulationState, n: int = 1) -> SimulationState:
    rng = random.Random(sim.world.seed + sim.world.turn * 1009)
    for _ in range(max(1, n)):
        choices = decide_actions(sim, rng)
        coop_ok, action_count = resolve_actions(sim, choices, rng)
        end_of_turn(sim, coop_ok, action_count)
        rng = random.Random(sim.world.seed + sim.world.turn * 1009)
    return sim
