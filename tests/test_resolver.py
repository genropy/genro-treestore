# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Tests for the TreeStore resolver system."""

import time

import pytest

from genro_toolbox import smartasync
from genro_treestore import TreeStore, TreeStoreNode, TreeStoreResolver, CallbackResolver


# =============================================================================
# Test Fixtures and Helper Classes
# =============================================================================


class CountingResolver(TreeStoreResolver):
    """Resolver that counts how many times load() is called."""

    def __init__(self, value, **kwargs):
        super().__init__(**kwargs)
        self.value_to_return = value
        self.load_count = 0
        self._init_args = (value,)

    @smartasync
    async def load(self):
        self.load_count += 1
        return self.value_to_return


class TreeStoreReturningResolver(TreeStoreResolver):
    """Resolver that returns a TreeStore (for traversal testing)."""

    def __init__(self, data: dict, **kwargs):
        super().__init__(**kwargs)
        self.data = data
        self._init_args = (data,)

    @smartasync
    async def load(self):
        return TreeStore(self.data)


class NestedResolver(TreeStoreResolver):
    """Resolver that returns a TreeStore with another resolver inside."""

    def __init__(self, outer_key: str, inner_resolver: TreeStoreResolver, **kwargs):
        super().__init__(**kwargs)
        self.outer_key = outer_key
        self.inner_resolver = inner_resolver
        self._init_args = (outer_key, inner_resolver)

    @smartasync
    async def load(self):
        store = TreeStore()
        store.set_item(self.outer_key)
        store.set_resolver(self.outer_key, self.inner_resolver)
        return store


# =============================================================================
# TreeStoreResolver Base Class Tests
# =============================================================================


class TestTreeStoreResolverInit:
    """Tests for TreeStoreResolver initialization."""

    def test_default_values(self):
        """Default cache_time=0 and read_only=True."""
        resolver = CountingResolver("value")
        assert resolver.cache_time == 0
        assert resolver.read_only is True
        assert resolver.parent_node is None
        assert resolver._cache is None

    def test_custom_cache_time(self):
        """Custom cache_time is stored correctly."""
        resolver = CountingResolver("value", cache_time=300)
        assert resolver.cache_time == 300

    def test_infinite_cache(self):
        """cache_time=-1 creates infinite cache."""
        resolver = CountingResolver("value", cache_time=-1)
        assert resolver.cache_time == -1
        assert resolver.expired  # Initially expired (no cache yet)

    def test_read_only_false(self):
        """read_only=False allows storing in node._value."""
        resolver = CountingResolver("value", read_only=False)
        assert resolver.read_only is False


class TestResolverCaching:
    """Tests for resolver caching behavior."""

    def test_no_cache_always_loads(self):
        """With cache_time=0, every access calls load()."""
        resolver = CountingResolver("value", cache_time=0)
        node = TreeStoreNode("test", resolver=resolver)

        _ = node.value
        _ = node.value
        _ = node.value

        assert resolver.load_count == 3

    def test_cache_prevents_reload(self):
        """With caching enabled, subsequent accesses use cache."""
        resolver = CountingResolver("value", cache_time=300)
        node = TreeStoreNode("test", resolver=resolver)

        _ = node.value
        _ = node.value
        _ = node.value

        assert resolver.load_count == 1

    def test_infinite_cache(self):
        """cache_time=-1 caches forever until reset."""
        resolver = CountingResolver("value", cache_time=-1)
        node = TreeStoreNode("test", resolver=resolver)

        _ = node.value
        _ = node.value

        assert resolver.load_count == 1

    def test_reset_invalidates_cache(self):
        """reset() forces reload on next access."""
        resolver = CountingResolver("value", cache_time=-1)
        node = TreeStoreNode("test", resolver=resolver)

        _ = node.value
        assert resolver.load_count == 1

        resolver.reset()
        _ = node.value
        assert resolver.load_count == 2

    def test_cache_expiration(self):
        """Cache expires after cache_time seconds."""
        resolver = CountingResolver("value", cache_time=1)
        node = TreeStoreNode("test", resolver=resolver)

        _ = node.value
        assert resolver.load_count == 1

        # Wait for cache to expire
        time.sleep(1.1)

        _ = node.value
        assert resolver.load_count == 2

    def test_expired_property_no_cache(self):
        """expired is True when cache_time=0."""
        resolver = CountingResolver("value", cache_time=0)
        assert resolver.expired is True

    def test_expired_property_no_timestamp(self):
        """expired is True when cache has never been populated."""
        resolver = CountingResolver("value", cache_time=300)
        assert resolver.expired is True


class TestResolverReadOnly:
    """Tests for read_only behavior."""

    def test_read_only_does_not_populate_value(self):
        """With read_only=True, node._value remains None."""
        resolver = CountingResolver("resolved_value", read_only=True)
        node = TreeStoreNode("test", resolver=resolver)

        result = node.value
        assert result == "resolved_value"
        assert node._value is None

    def test_not_read_only_populates_value(self):
        """With read_only=False, node._value is populated."""
        resolver = CountingResolver("resolved_value", read_only=False, cache_time=-1)
        node = TreeStoreNode("test", resolver=resolver)

        result = node.value
        assert result == "resolved_value"
        assert node._value == "resolved_value"


# =============================================================================
# CallbackResolver Tests
# =============================================================================


class TestCallbackResolver:
    """Tests for CallbackResolver."""

    def test_basic_callback(self):
        """Callback is invoked with parent_node."""

        def my_callback(node):
            return f"Hello from {node.label}"

        resolver = CallbackResolver(my_callback)
        node = TreeStoreNode("test_node", resolver=resolver)

        assert node.value == "Hello from test_node"

    def test_callback_accesses_parent_store(self):
        """Callback can access siblings via node.parent."""

        def compute_sum(node):
            store = node.parent
            return store.get_item("a") + store.get_item("b")

        store = TreeStore()
        store.set_item("a", 10)
        store.set_item("b", 20)
        store.set_item("sum")
        store.set_resolver("sum", CallbackResolver(compute_sum))

        assert store["sum"] == 30

    def test_callback_with_caching(self):
        """CallbackResolver respects cache_time."""
        call_count = 0

        def counting_callback(node):
            nonlocal call_count
            call_count += 1
            return call_count

        resolver = CallbackResolver(counting_callback, cache_time=-1)
        node = TreeStoreNode("test", resolver=resolver)

        assert node.value == 1
        assert node.value == 1  # Cached
        assert call_count == 1


# =============================================================================
# TreeStore Integration Tests
# =============================================================================


class TestTreeStoreResolverIntegration:
    """Tests for resolver integration with TreeStore."""

    def test_set_resolver_get_resolver(self):
        """set_resolver and get_resolver work correctly."""
        store = TreeStore()
        store.set_item("data", "initial")

        resolver = CountingResolver("resolved")
        store.set_resolver("data", resolver)

        assert store.get_resolver("data") is resolver

    def test_node_value_uses_resolver(self):
        """Accessing node.value triggers the resolver."""
        store = TreeStore()
        store.set_item("data", "initial")

        resolver = CountingResolver("resolved", cache_time=-1)
        store.set_resolver("data", resolver)

        assert store["data"] == "resolved"
        assert resolver.load_count == 1

    def test_resolver_in_path_traversal(self):
        """Resolver in middle of path is resolved for traversal."""
        store = TreeStore()
        store.set_item("remote")

        inner_data = {"file": {"_value": "content"}}
        resolver = TreeStoreReturningResolver(inner_data, cache_time=-1)
        store.set_resolver("remote", resolver)

        # Access through the resolver
        assert store["remote.file"] == "content"

    def test_multiple_resolvers_in_path(self):
        """Multiple resolvers in a path are resolved in sequence."""
        store = TreeStore()
        store.set_item("level1")

        # Inner resolver returns final value
        inner_resolver = CountingResolver("final_value", cache_time=-1)

        # Outer resolver returns TreeStore with inner resolver
        outer_resolver = NestedResolver("level2", inner_resolver, cache_time=-1)
        store.set_resolver("level1", outer_resolver)

        # Access through both resolvers
        result = store["level1.level2"]
        assert result == "final_value"

    def test_traversal_always_populates_value(self):
        """During traversal, node._value is always populated (regardless of read_only)."""
        store = TreeStore()
        store.set_item("remote")

        inner_data = {"child": {"_value": "data"}}
        # Note: read_only=True, but traversal should still populate
        resolver = TreeStoreReturningResolver(inner_data, cache_time=-1, read_only=True)
        store.set_resolver("remote", resolver)

        # Access through the resolver
        _ = store["remote.child"]

        # The node's _value should be populated for traversal to work
        remote_node = store.get_node("remote")
        assert isinstance(remote_node._value, TreeStore)


# =============================================================================
# Serialization Tests
# =============================================================================


class TestResolverSerialization:
    """Tests for resolver serialization/deserialization."""

    def test_serialize_basic_resolver(self):
        """serialize() produces correct structure."""
        resolver = CountingResolver("value", cache_time=300, read_only=False)
        data = resolver.serialize()

        assert data["resolver_module"] == "tests.test_resolver"
        assert data["resolver_class"] == "CountingResolver"
        assert data["args"] == ("value",)
        assert data["kwargs"]["cache_time"] == 300
        assert data["kwargs"]["read_only"] is False

    def test_deserialize_recreates_resolver(self):
        """deserialize() recreates the resolver correctly."""
        original = CountingResolver("test_value", cache_time=600)
        data = original.serialize()

        # Deserialize
        recreated = TreeStoreResolver.deserialize(data)

        assert isinstance(recreated, CountingResolver)
        assert recreated.value_to_return == "test_value"
        assert recreated.cache_time == 600

    def test_callback_resolver_serialization(self):
        """CallbackResolver serializes the callback function."""

        def my_func(node):
            return "result"

        resolver = CallbackResolver(my_func, cache_time=100)
        data = resolver.serialize()

        assert data["resolver_class"] == "CallbackResolver"
        assert data["args"][0] is my_func


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestResolverEdgeCases:
    """Tests for edge cases and error handling."""

    def test_resolver_without_parent_node(self):
        """Resolver works even without parent_node set."""
        resolver = CountingResolver("value")
        # Manually call _htraverse without setting parent_node
        result = resolver._htraverse()
        assert result == "value"

    def test_resolver_with_remaining_path_non_treestore(self):
        """remaining_path is ignored if result is not a TreeStore."""
        resolver = CountingResolver("scalar_value", cache_time=-1)
        TreeStoreNode("test", resolver=resolver)

        # _htraverse with remaining_path on non-TreeStore result
        result = resolver._htraverse("some.path")
        assert result == "scalar_value"  # Path ignored, returns scalar

    def test_get_node_through_resolver(self):
        """get_node works through resolver that returns TreeStore."""
        store = TreeStore()
        store.set_item("remote")

        inner_data = {"child": {"_value": "data"}}
        resolver = TreeStoreReturningResolver(inner_data, cache_time=-1)
        store.set_resolver("remote", resolver)

        # get_node should work through the resolver
        node = store.get_node("remote.child")
        assert node.label == "child"
        assert node.value == "data"

    def test_resolver_parent_node_set_on_assignment(self):
        """parent_node is set when resolver is assigned to node."""
        resolver = CountingResolver("value")
        node = TreeStoreNode("test")

        assert resolver.parent_node is None

        node.resolver = resolver
        assert resolver.parent_node is node

    def test_resolver_repr(self):
        """__repr__ produces readable output."""
        resolver = CountingResolver("value", cache_time=300)
        repr_str = repr(resolver)

        assert "CountingResolver" in repr_str
        assert "cache_time=300" in repr_str

    def test_base_resolver_load_raises(self):
        """TreeStoreResolver.load() raises NotImplementedError."""
        resolver = TreeStoreResolver()
        with pytest.raises(NotImplementedError, match="must implement load"):
            resolver.load()

    def test_htraverse_with_remaining_path_on_treestore(self):
        """_htraverse with remaining_path continues into TreeStore."""
        inner_data = {"deep": {"_value": "found_it"}}
        resolver = TreeStoreReturningResolver(inner_data, cache_time=-1)
        TreeStoreNode("test", resolver=resolver)

        # Access with remaining path
        result = resolver._htraverse("deep")
        assert result == "found_it"

    def test_callback_resolver_repr_with_lambda(self):
        """CallbackResolver.__repr__ handles lambda functions."""
        resolver = CallbackResolver(lambda n: n.label)
        repr_str = repr(resolver)
        assert "CallbackResolver" in repr_str
        # Lambda doesn't have a nice __name__
        assert "<lambda>" in repr_str or "lambda" in repr_str.lower()
