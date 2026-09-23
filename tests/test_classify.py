"""Классификация. Голова эпика важнее метки. Без головы — unknown, не техника."""

from dashboard.config.model import Epics, Taxonomy
from dashboard.metrics.engine import compute
from tests.support import at, bundle, change, issue, link, team


def _taxonomy(**kwargs) -> Taxonomy:
    raw = dict(
        priority=("project", "tech"),
        epics=Epics(project=("P-1",), tech=("T-1",)),
        link_types=("Child-Issue",),
        rules=(),
        prod_label="prod_op",
        tech_label="other_tech",
    )
    raw.update(kwargs)
    return Taxonomy(**raw)


def test_diamond_cycle_label_and_unknown():
    project = issue("P-1", id="p", type="Epic", status="In Progress")
    tech = issue("T-1", id="t", type="Epic")
    diamond = issue("D-1", labels=("other_tech",))
    cycle_a = issue("A-1")
    cycle_b = issue("B-1")
    labeled = issue("L-1", labels=("other_tech",))
    unknown = issue("U-1")
    blocked = issue("K-1")
    issues = [project, tech, diamond, cycle_a, cycle_b, labeled, unknown, blocked]
    links = [
        link("p", "D-1"),
        link("t", "D-1"),
        link("p", "A-1"),
        link("A-1", "B-1"),
        link("B-1", "A-1"),
        link("p", "L-1"),
        link("p", "K-1", "Blocks"),
    ]
    data = bundle(issues, links=tuple(links), as_of=at("2026-09-09T16:00:00Z"))
    metric = next(
        item
        for item in compute(data, team(taxonomy=_taxonomy()), as_of=data.as_of).period_metrics
        if item.id == "classification"
    )
    paths = {item["issueKey"]: item for item in metric.detail["paths"]}
    assert paths["D-1"]["headId"] == "p"
    assert paths["D-1"]["category"] == "project"
    assert paths["A-1"]["headId"] == "p"
    assert paths["B-1"]["headId"] == "p"
    assert paths["L-1"]["reason"] == "head"
    assert paths["L-1"]["category"] == "project"
    assert paths["U-1"]["reason"] == "unknown"
    assert paths["K-1"]["reason"] == "unknown"
    assert metric.value == 100 * 2 / 6
    assert "unknown-above-threshold" in metric.warnings


def test_same_depth_tie_uses_smaller_parent_id():
    first = issue("A-1", id="a-epic", type="Epic")
    second = issue("B-2", id="b-epic", type="Epic")
    child = issue("X-1")
    data = bundle(
        [first, second, child],
        links=(link("b-epic", "X-1"), link("a-epic", "X-1")),
        as_of=at("2026-09-09T16:00:00Z"),
    )
    taxonomy = _taxonomy(epics=Epics(project=("A-1", "B-2"), tech=()))
    metric = next(
        item
        for item in compute(data, team(taxonomy=taxonomy), as_of=data.as_of).period_metrics
        if item.id == "classification"
    )
    path = next(item for item in metric.detail["paths"] if item["issueKey"] == "X-1")
    assert path["headId"] == "a-epic"


def test_rule_applies_only_without_a_head():
    from dashboard.config.model import Rule

    lone = issue("R-1", labels=("tech-debt",))
    data = bundle([lone], as_of=at("2026-09-09T16:00:00Z"))
    taxonomy = _taxonomy(rules=(Rule(category="tech", label="tech-debt", project_key=None),))
    metric = next(
        item
        for item in compute(data, team(taxonomy=taxonomy), as_of=data.as_of).period_metrics
        if item.id == "classification"
    )
    path = metric.detail["paths"][0]
    assert path["reason"] == "rule"
    assert path["category"] == "tech"
