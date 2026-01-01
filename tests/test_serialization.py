# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Tests for TreeStore TYTX serialization.

These tests verify that TreeStore can be serialized to and deserialized from
TYTX format, preserving:
- Tree structure (hierarchy, parent-child relationships)
- Node values with correct types (Decimal, date, datetime, time)
- Node attributes
- Node tags from builders

Note on datetime handling:
    TYTX serializes all datetimes as UTC with millisecond precision.
    On deserialization, naive datetimes become aware (UTC).
    Use tytx_equivalent() for roundtrip comparison.

Note:
    These tests require genro-tytx package. They are skipped if not installed.
"""

from datetime import date, datetime, time
from decimal import Decimal

from genro_tytx.utils import tytx_equivalent

from genro_treestore import TreeStore, BuilderBase


class TestFlattened:
    """Tests for the flattened() iterator method."""

    def test_flattened_empty_store(self):
        """Empty store yields nothing."""
        store = TreeStore()
        rows = list(store.flattened())
        assert rows == []

    def test_flattened_single_leaf(self):
        """Single leaf node yields one row."""
        store = TreeStore()
        store.set_item("key", "value")

        rows = list(store.flattened())

        assert len(rows) == 1
        parent, label, tag, value, attr = rows[0]
        assert parent == ""
        assert label == "key"
        assert tag is None
        assert value == "value"
        assert attr == {}

    def test_flattened_nested_structure(self):
        """Nested structure yields rows in depth-first order."""
        store = TreeStore()
        store.set_item("a.b.c", "leaf")

        rows = list(store.flattened())

        assert len(rows) == 3
        # First: 'a' (branch)
        assert rows[0][0] == ""  # parent
        assert rows[0][1] == "a"  # label
        assert rows[0][3] is None  # value (branch)
        # Second: 'a.b' (branch)
        assert rows[1][0] == "a"  # parent
        assert rows[1][1] == "b"  # label
        assert rows[1][3] is None  # value (branch)
        # Third: 'a.b.c' (leaf)
        assert rows[2][0] == "a.b"  # parent
        assert rows[2][1] == "c"  # label
        assert rows[2][3] == "leaf"  # value

    def test_flattened_with_attributes(self):
        """Node attributes are included in output."""
        store = TreeStore()
        store.set_item("node", "val", color="red", size=10)

        rows = list(store.flattened())

        assert len(rows) == 1
        _, _, _, _, attr = rows[0]
        assert attr == {"color": "red", "size": 10}

    def test_flattened_compact_mode(self):
        """Compact mode uses numeric codes for parent references."""
        store = TreeStore()
        store.set_item("a.b.c", "leaf")

        paths = {}
        rows = list(store.flattened(path_registry=paths))

        # First row: root-level node, parent is None
        assert rows[0][0] is None
        assert rows[0][1] == "a"

        # Second row: child of 'a', parent is code 0
        assert rows[1][0] == 0
        assert rows[1][1] == "b"

        # Third row: child of 'a.b', parent is code 1
        assert rows[2][0] == 1
        assert rows[2][1] == "c"

        # paths registry maps codes to full paths
        assert paths == {0: "a", 1: "a.b"}


class TestToTytx:
    """Tests for to_tytx() serialization."""

    def test_to_tytx_basic(self):
        """Basic serialization produces JSON string."""
        store = TreeStore()
        store.set_item("key", "value")

        result = store.to_tytx()

        assert isinstance(result, str)
        assert "rows" in result
        assert "key" in result

    def test_to_tytx_msgpack(self):
        """MessagePack transport produces bytes."""
        store = TreeStore()
        store.set_item("key", "value")

        result = store.to_tytx(transport="msgpack")

        assert isinstance(result, bytes)

    def test_to_tytx_compact(self):
        """Compact mode includes paths registry."""
        store = TreeStore()
        store.set_item("a.b", "value")

        result = store.to_tytx(compact=True)

        assert isinstance(result, str)
        assert "paths" in result


class TestFromTytx:
    """Tests for from_tytx() deserialization."""

    def test_from_tytx_basic(self):
        """Basic deserialization reconstructs structure."""
        store = TreeStore()
        store.set_item("config.name", "MyApp")
        store.set_item("config.version", "1.0")

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        assert restored["config.name"] == "MyApp"
        assert restored["config.version"] == "1.0"

    def test_from_tytx_msgpack(self):
        """MessagePack round-trip works."""
        store = TreeStore()
        store.set_item("key", "value")

        data = store.to_tytx(transport="msgpack")
        restored = TreeStore.from_tytx(data, transport="msgpack")

        assert restored["key"] == "value"

    def test_from_tytx_compact(self):
        """Compact mode round-trip works."""
        store = TreeStore()
        store.set_item("a.b.c", "deep")

        data = store.to_tytx(compact=True)
        restored = TreeStore.from_tytx(data)

        assert restored["a.b.c"] == "deep"


class TestTypePreservation:
    """Tests for type preservation across serialization."""

    def test_decimal_preserved(self):
        """Decimal values are preserved exactly."""
        store = TreeStore()
        store.set_item("price", Decimal("1234.56"))
        store.set_item("tax", Decimal("0.07"))

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        assert restored["price"] == Decimal("1234.56")
        assert restored["tax"] == Decimal("0.07")
        assert isinstance(restored["price"], Decimal)
        assert isinstance(restored["tax"], Decimal)

    def test_date_preserved(self):
        """Date values are preserved."""
        store = TreeStore()
        store.set_item("birthday", date(1990, 5, 15))

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        assert restored["birthday"] == date(1990, 5, 15)
        assert isinstance(restored["birthday"], date)

    def test_datetime_preserved(self):
        """Datetime values are preserved (naive becomes aware UTC)."""
        store = TreeStore()
        dt = datetime(2025, 1, 15, 10, 30, 45)
        store.set_item("created", dt)

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        # TYTX treats naive as UTC on serialize, returns aware UTC on deserialize
        assert tytx_equivalent(dt, restored["created"])
        assert isinstance(restored["created"], datetime)

    def test_time_preserved(self):
        """Time values are preserved."""
        store = TreeStore()
        t = time(14, 30, 0)
        store.set_item("meeting", t)

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        assert restored["meeting"] == t
        assert isinstance(restored["meeting"], time)

    def test_mixed_types(self):
        """Multiple typed values in one store."""
        store = TreeStore()
        created_dt = datetime(2025, 1, 1, 9, 0, 0)
        store.set_item("invoice.amount", Decimal("999.99"))
        store.set_item("invoice.date", date(2025, 1, 1))
        store.set_item("invoice.created", created_dt)
        store.set_item("invoice.paid", False)
        store.set_item("invoice.items", 5)

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        assert restored["invoice.amount"] == Decimal("999.99")
        assert restored["invoice.date"] == date(2025, 1, 1)
        assert tytx_equivalent(created_dt, restored["invoice.created"])
        assert restored["invoice.paid"] is False
        assert restored["invoice.items"] == 5

    def test_types_in_msgpack(self):
        """Types are preserved in msgpack format too."""
        store = TreeStore()
        store.set_item("price", Decimal("50.00"))
        store.set_item("when", date(2025, 6, 15))

        data = store.to_tytx(transport="msgpack")
        restored = TreeStore.from_tytx(data, transport="msgpack")

        assert isinstance(restored["price"], Decimal)
        assert isinstance(restored["when"], date)


class TestAttributePreservation:
    """Tests for node attribute preservation."""

    def test_simple_attributes(self):
        """Simple string/number attributes are preserved."""
        store = TreeStore()
        store.set_item("node", "value", color="red", count=42)

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        node = restored.get_node("node")
        assert node.attr["color"] == "red"
        assert node.attr["count"] == 42

    def test_typed_attributes(self):
        """Typed values in attributes are preserved."""
        store = TreeStore()
        store.set_item("item", "value", price=Decimal("19.99"))

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        node = restored.get_node("item")
        assert node.attr["price"] == Decimal("19.99")
        assert isinstance(node.attr["price"], Decimal)

    def test_nested_attributes(self):
        """Attributes on nested nodes are preserved."""
        store = TreeStore()
        store.set_item("a.b.c", "leaf", level=3)

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        node = restored.get_node("a.b.c")
        assert node.attr["level"] == 3


class TestBuilderPreservation:
    """Tests for tag preservation from builders."""

    def test_tag_preserved(self):
        """Node tags from builder are preserved."""

        class SimpleBuilder(BuilderBase):
            _schema = {"item": {}}

        store = TreeStore(builder=SimpleBuilder())
        store.item(name="test")

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        node = restored.get_node("#0")
        assert node.tag == "item"
        assert node.attr["name"] == "test"


class TestComplexStructures:
    """Tests for complex tree structures."""

    def test_wide_tree(self):
        """Tree with many siblings."""
        store = TreeStore()
        for i in range(10):
            store.set_item(f"item_{i}", i)

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        assert len(restored) == 10
        for i in range(10):
            assert restored[f"item_{i}"] == i

    def test_deep_tree(self):
        """Deeply nested tree."""
        store = TreeStore()
        path = ".".join([f"level{i}" for i in range(10)])
        store.set_item(path, "deep_value")

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        assert restored[path] == "deep_value"

    def test_mixed_tree(self):
        """Tree with both branches and leaves at various levels."""
        store = TreeStore()
        store.set_item("a", 1)
        store.set_item("b.x", 2)
        store.set_item("b.y", 3)
        store.set_item("c.d.e", 4)
        store.set_item("c.f", 5)

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        assert restored["a"] == 1
        assert restored["b.x"] == 2
        assert restored["b.y"] == 3
        assert restored["c.d.e"] == 4
        assert restored["c.f"] == 5


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_store(self):
        """Empty store serializes and deserializes correctly."""
        store = TreeStore()

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        assert len(restored) == 0

    def test_none_value_creates_branch(self):
        """Setting None value creates a branch node (container for children)."""
        store = TreeStore()
        store.set_item("container", None)

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        # None value in set_item creates a branch (empty container)
        node = restored.get_node("container")
        assert node.is_branch
        assert len(node.value) == 0  # Empty TreeStore

    def test_empty_string_value(self):
        """Empty string values are preserved."""
        store = TreeStore()
        store.set_item("empty", "")

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        assert restored["empty"] == ""

    def test_zero_values(self):
        """Zero numeric values are preserved."""
        store = TreeStore()
        store.set_item("zero_int", 0)
        store.set_item("zero_float", 0.0)
        store.set_item("zero_decimal", Decimal("0"))

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        assert restored["zero_int"] == 0
        assert restored["zero_float"] == 0.0
        assert restored["zero_decimal"] == Decimal("0")

    def test_boolean_values(self):
        """Boolean values are preserved correctly."""
        store = TreeStore()
        store.set_item("yes", True)
        store.set_item("no", False)

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        assert restored["yes"] is True
        assert restored["no"] is False

    def test_special_characters_in_labels(self):
        """Labels with special characters work."""
        store = TreeStore()
        store.set_item("item-with-dash", 1)
        store.set_item("item_with_underscore", 2)

        data = store.to_tytx()
        restored = TreeStore.from_tytx(data)

        assert restored["item-with-dash"] == 1
        assert restored["item_with_underscore"] == 2
