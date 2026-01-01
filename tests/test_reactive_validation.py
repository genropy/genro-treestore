# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Tests for reactive validation with _invalid_reasons."""

import pytest

from genro_treestore import TreeStore, TreeStoreNode, BuilderBase, ValidationSubscriber
from genro_treestore.builders.decorators import element


# Test builders with validation rules


class TableBuilder(BuilderBase):
    """Builder for table elements with cardinality constraints."""

    @element(children='tr[1:]')  # At least 1 tr required
    def thead(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element(children='tr')  # Any number of tr
    def tbody(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element(children='th, td')  # th or td children
    def tr(self, target, tag, **attr):
        return self.child(target, tag, **attr)

    @element()  # Leaf element
    def th(self, target, tag, value='', **attr):
        return self.child(target, tag, value=value, **attr)

    @element()  # Leaf element
    def td(self, target, tag, value='', **attr):
        return self.child(target, tag, value=value, **attr)

    @element(children='thead[1], tbody[1]')  # Exactly 1 thead and 1 tbody
    def table(self, target, tag, **attr):
        return self.child(target, tag, **attr)


class FormBuilder(BuilderBase):
    """Builder with attribute validation via schema."""

    _schema = {
        'input': {
            'leaf': True,
            'attrs': {
                'type': {'type': 'enum', 'values': ['text', 'number', 'email'], 'required': True},
                'maxlength': {'type': 'int', 'min': 1, 'max': 1000},
            }
        },
        'select': {
            'children': 'option[1:]',  # At least 1 option required
        },
        'option': {
            'leaf': True,
        },
    }


class TestNodeInvalidReasons:
    """Test _invalid_reasons on TreeStoreNode."""

    def test_node_has_invalid_reasons_attribute(self):
        """Node should have _invalid_reasons list."""
        node = TreeStoreNode('test', {}, 'value')
        assert hasattr(node, '_invalid_reasons')
        assert node._invalid_reasons == []

    def test_node_is_valid_when_no_errors(self):
        """Node.is_valid should be True when no errors."""
        node = TreeStoreNode('test', {}, 'value')
        assert node.is_valid is True

    def test_node_is_invalid_when_has_errors(self):
        """Node.is_valid should be False when has errors."""
        node = TreeStoreNode('test', {}, 'value')
        node._invalid_reasons.append('test error')
        assert node.is_valid is False


class TestReactiveValidationCardinality:
    """Test reactive validation for children cardinality constraints."""

    def test_thead_requires_at_least_one_tr(self):
        """thead with children='tr[1:]' should be invalid without tr."""
        store = TreeStore(builder=TableBuilder())
        store.thead()

        # thead node should have cardinality error
        thead_node = store.get_node('thead_0')
        assert not thead_node.is_valid
        assert any("requires at least 1 'tr'" in e for e in thead_node._invalid_reasons)

    def test_thead_becomes_valid_after_adding_tr(self):
        """thead should become valid after adding required tr."""
        store = TreeStore(builder=TableBuilder())
        thead = store.thead()
        thead_node = store.get_node('thead_0')

        # Initially invalid
        assert not thead_node.is_valid

        # Add tr
        thead.tr()

        # Now valid
        assert thead_node.is_valid
        assert thead_node._invalid_reasons == []

    def test_thead_becomes_invalid_after_deleting_tr(self):
        """thead should become invalid after deleting required tr."""
        store = TreeStore(builder=TableBuilder())
        thead = store.thead()
        thead.tr()

        thead_node = store.get_node('thead_0')
        assert thead_node.is_valid

        # Delete the tr
        thead.del_item('tr_0')

        # Now invalid again
        assert not thead_node.is_valid
        assert any("requires at least 1 'tr'" in e for e in thead_node._invalid_reasons)

    def test_table_requires_exactly_one_thead(self):
        """table with children='thead[1], tbody[1]' should require exactly one."""
        store = TreeStore(builder=TableBuilder())
        store.table()

        table_node = store.get_node('table_0')
        # Should be invalid - missing thead and tbody
        assert not table_node.is_valid
        assert any("requires at least 1 'thead'" in e for e in table_node._invalid_reasons)
        assert any("requires at least 1 'tbody'" in e for e in table_node._invalid_reasons)

    def test_tbody_allows_any_number_of_tr(self):
        """tbody with children='tr' should allow any number."""
        store = TreeStore(builder=TableBuilder())
        store.tbody()

        tbody_node = store.get_node('tbody_0')
        # Should be valid even without tr (no min constraint)
        assert tbody_node.is_valid


class TestReactiveValidationAttributes:
    """Test reactive validation for attribute constraints.

    These tests use raise_on_error=False to allow errors to be collected
    instead of raising exceptions immediately.
    """

    def test_missing_required_attribute(self):
        """Missing required attribute should add error."""
        store = TreeStore(builder=FormBuilder(), raise_on_error=False)
        # input requires 'type' attribute
        store.input()

        input_node = store.get_node('input_0')
        assert not input_node.is_valid
        assert any("'type' is required" in e for e in input_node._invalid_reasons)

    def test_valid_required_attribute(self):
        """Valid required attribute should not add error."""
        store = TreeStore(builder=FormBuilder(), raise_on_error=False)
        store.input(type='text')

        input_node = store.get_node('input_0')
        assert input_node.is_valid

    def test_invalid_enum_attribute(self):
        """Invalid enum value should add error."""
        store = TreeStore(builder=FormBuilder(), raise_on_error=False)
        store.input(type='invalid_type')

        input_node = store.get_node('input_0')
        assert not input_node.is_valid
        assert any("must be one of" in e for e in input_node._invalid_reasons)

    def test_integer_min_constraint(self):
        """Integer below min should add error."""
        store = TreeStore(builder=FormBuilder(), raise_on_error=False)
        store.input(type='text', maxlength=0)  # min is 1

        input_node = store.get_node('input_0')
        assert not input_node.is_valid
        assert any("must be >= 1" in e for e in input_node._invalid_reasons)


class TestStoreValidation:
    """Test TreeStore validation methods."""

    def test_store_is_valid_when_all_nodes_valid(self):
        """Store.is_valid should be True when all nodes are valid."""
        store = TreeStore(builder=TableBuilder())
        tbody = store.tbody()
        tr = tbody.tr()
        tr.td(value='cell')

        assert store.is_valid

    def test_store_is_invalid_when_any_node_invalid(self):
        """Store.is_valid should be False when any node is invalid."""
        store = TreeStore(builder=TableBuilder())
        store.thead()  # Missing required tr

        assert not store.is_valid

    def test_validation_errors_returns_all_errors(self):
        """validation_errors() should return dict of all errors."""
        store = TreeStore(builder=TableBuilder())
        store.thead()  # Missing required tr

        errors = store.validation_errors()
        assert 'thead_0' in errors
        assert len(errors['thead_0']) > 0

    def test_validation_errors_empty_when_valid(self):
        """validation_errors() should return empty dict when valid."""
        store = TreeStore(builder=TableBuilder())
        tbody = store.tbody()
        tbody.tr()

        errors = store.validation_errors()
        assert errors == {}


class TestRaiseOnErrorParameter:
    """Test raise_on_error parameter behavior."""

    def test_raise_on_error_true_by_default(self):
        """raise_on_error should be True by default."""
        store = TreeStore(builder=TableBuilder())
        assert store._raise_on_error is True

    def test_validator_always_registered_with_builder(self):
        """ValidationSubscriber should always be registered when builder is set."""
        store = TreeStore(builder=TableBuilder())
        assert store._validator is not None
        assert isinstance(store._validator, ValidationSubscriber)

    def test_validator_registered_when_raise_on_error_false(self):
        """ValidationSubscriber should be registered even when raise_on_error=False."""
        store = TreeStore(builder=FormBuilder(), raise_on_error=False)
        assert store._validator is not None
        assert isinstance(store._validator, ValidationSubscriber)

    def test_no_validator_without_builder(self):
        """No validator should be registered without a builder."""
        store = TreeStore()
        assert store._validator is None

    def test_raise_on_error_false_allows_invalid_attrs_without_raising(self):
        """With raise_on_error=False, invalid attrs should not raise."""
        store = TreeStore(builder=FormBuilder(), raise_on_error=False)
        # This should NOT raise even though 'type' is required
        store.input()  # Missing required 'type' attribute

        # But errors should still be collected
        input_node = store.get_node('input_0')
        assert not input_node.is_valid
        assert any("'type' is required" in e for e in input_node._invalid_reasons)

    def test_raise_on_error_true_raises_on_invalid_attrs(self):
        """With raise_on_error=True (default), invalid attrs should raise."""
        store = TreeStore(builder=FormBuilder(), raise_on_error=True)
        with pytest.raises(ValueError, match="'type' is required"):
            store.input()  # Missing required 'type' attribute


class TestSelectOptionCardinality:
    """Test select/option cardinality from FormBuilder schema."""

    def test_select_requires_at_least_one_option(self):
        """select with children='option[1:]' should be invalid without option."""
        store = TreeStore(builder=FormBuilder())
        store.select()

        select_node = store.get_node('select_0')
        assert not select_node.is_valid
        assert any("requires at least 1 'option'" in e for e in select_node._invalid_reasons)

    def test_select_valid_with_option(self):
        """select should be valid after adding option."""
        store = TreeStore(builder=FormBuilder())
        select = store.select()
        select.option(value='Choice 1')

        select_node = store.get_node('select_0')
        assert select_node.is_valid

    def test_select_invalid_after_removing_last_option(self):
        """select should become invalid after removing last option."""
        store = TreeStore(builder=FormBuilder())
        select = store.select()
        select.option(value='Choice 1')

        select_node = store.get_node('select_0')
        assert select_node.is_valid

        # Remove the option
        select.del_item('option_0')

        assert not select_node.is_valid
        assert any("requires at least 1 'option'" in e for e in select_node._invalid_reasons)
