from awr.models import Status, WorkItem
from awr.registry import WorkRegistry
from awr.scheduler import Scheduler


def test_scheduler_respects_dependencies():
    registry = WorkRegistry()
    first = registry.add(WorkItem(title="Clean CSV", status=Status.READY, priority=1))
    second = registry.add(WorkItem(title="Generate dashboard", status=Status.READY, priority=10, dependency_ids=[first.id]))

    assert Scheduler(registry).ready() == [first]

    registry.update_status(first.id, Status.COMPLETED)

    assert Scheduler(registry).ready()[0].id == second.id


def test_registry_records_lineage_and_events():
    registry = WorkRegistry()
    parent = registry.add(WorkItem(title="Research competitors"))
    child = registry.add(WorkItem(title="Search companies", parent_id=parent.id))

    reloaded_parent = registry.get(parent.id)

    assert child.id in reloaded_parent.child_ids
    assert [event.type for event in registry.events()] == ["TaskCreated", "TaskCreated"]


def test_terminal_items_cannot_be_reopened():
    item = WorkItem(title="Deploy application", status=Status.COMPLETED)

    try:
        item.transition_to(Status.RUNNING)
    except ValueError as error:
        assert "cannot transition terminal" in str(error)
    else:
        raise AssertionError("terminal transition should fail")
