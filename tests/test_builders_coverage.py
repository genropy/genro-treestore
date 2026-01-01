# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Tests to improve coverage on builders modules."""

import pytest
from typing import Literal
from genro_treestore import TreeStore
from genro_treestore.builders import BuilderBase, HtmlBuilder
from genro_treestore.builders.decorators import (
    element,
    _parse_tag_spec,
    _parse_tags,
    _annotation_to_attr_spec,
    _extract_attrs_from_signature,
    _validate_attrs_from_spec,
)
from genro_treestore.builders.html import HtmlPage


class TestParseTagSpec:
    """Tests for _parse_tag_spec function."""

    def test_invalid_tag_spec_raises(self):
        """Test that invalid tag spec raises ValueError."""
        with pytest.raises(ValueError, match="Invalid tag specification"):
            _parse_tag_spec("123invalid")

        with pytest.raises(ValueError, match="Invalid tag specification"):
            _parse_tag_spec("tag[abc]")


class TestParseTags:
    """Tests for _parse_tags function."""

    def test_parse_tuple_tags(self):
        """Test parsing tuple of tags."""
        result = _parse_tags(("foo", "bar", "baz"))
        assert result == ["foo", "bar", "baz"]

    def test_parse_empty_tuple(self):
        """Test parsing empty tuple."""
        result = _parse_tags(())
        assert result == []

    def test_parse_string_tags(self):
        """Test parsing comma-separated string tags."""
        result = _parse_tags("foo, bar, baz")
        assert result == ["foo", "bar", "baz"]


class TestAnnotationToAttrSpec:
    """Tests for _annotation_to_attr_spec function."""

    def test_union_multiple_types(self):
        """Test Union with multiple non-None types falls back to string."""
        from typing import Union
        result = _annotation_to_attr_spec(Union[int, str])
        assert result == {"type": "string"}

    def test_unknown_type_defaults_to_string(self):
        """Test unknown type defaults to string."""
        result = _annotation_to_attr_spec(list)
        assert result == {"type": "string"}


class TestExtractAttrsFromSignature:
    """Tests for _extract_attrs_from_signature function."""

    def test_skip_var_positional(self):
        """Test that *args is skipped."""
        def func(self, target, tag, *args, x: int = 1):
            pass
        result = _extract_attrs_from_signature(func)
        assert "args" not in result
        assert "x" in result

    def test_no_typed_params_returns_none(self):
        """Test function with no typed params returns None."""
        def func(self, target, tag, **kwargs):
            pass
        result = _extract_attrs_from_signature(func)
        assert result is None

    def test_literal_annotation(self):
        """Test Literal annotation creates enum type."""
        def func(scope: Literal['row', 'col'] = None):
            pass
        result = _extract_attrs_from_signature(func)
        assert result["scope"]["type"] == "enum"
        assert result["scope"]["values"] == ['row', 'col']

    def test_required_param(self):
        """Test parameter without default is marked required."""
        def func(required_param: int):
            pass
        result = _extract_attrs_from_signature(func)
        assert result["required_param"]["required"] is True

    def test_optional_with_default(self):
        """Test parameter with default is not required."""
        def func(optional_param: int = 42):
            pass
        result = _extract_attrs_from_signature(func)
        assert result["optional_param"]["required"] is False
        assert result["optional_param"]["default"] == 42

    def test_param_without_annotation_skipped(self):
        """Test parameter without type annotation is skipped (line 106)."""
        def func(self, target, tag, untyped_param, typed_param: int = 1):
            pass
        result = _extract_attrs_from_signature(func)
        assert "untyped_param" not in result
        assert "typed_param" in result

    def test_optional_type_annotation(self):
        """Test Optional[X] annotation extracts inner type (line 144)."""
        from typing import Optional
        def func(opt_int: Optional[int] = None):
            pass
        result = _extract_attrs_from_signature(func)
        assert result["opt_int"]["type"] == "int"

    def test_bool_annotation(self):
        """Test bool annotation creates bool type (line 156)."""
        def func(flag: bool = False):
            pass
        result = _extract_attrs_from_signature(func)
        assert result["flag"]["type"] == "bool"

    def test_str_annotation(self):
        """Test str annotation creates string type (line 158)."""
        def func(name: str = "default"):
            pass
        result = _extract_attrs_from_signature(func)
        assert result["name"]["type"] == "string"


class TestValidateAttrsFromSpec:
    """Tests for _validate_attrs_from_spec function."""

    def test_optional_none_skipped(self):
        """Test optional param with None value is skipped (line 323)."""
        spec = {"optional": {"required": False, "type": "int"}}
        # Should not raise - None is acceptable for optional param
        _validate_attrs_from_spec(spec, {"optional": None})

    def test_required_missing_raises(self):
        """Test missing required attr raises ValueError."""
        spec = {"name": {"required": True, "type": "string"}}
        with pytest.raises(ValueError, match="'name' is required"):
            _validate_attrs_from_spec(spec, {})

    def test_int_conversion_fails(self):
        """Test invalid int conversion raises."""
        spec = {"count": {"type": "int"}}
        with pytest.raises(ValueError, match="must be an integer"):
            _validate_attrs_from_spec(spec, {"count": "not_a_number"})

    def test_bool_invalid_string(self):
        """Test invalid bool string raises."""
        spec = {"flag": {"type": "bool"}}
        with pytest.raises(ValueError, match="must be a boolean"):
            _validate_attrs_from_spec(spec, {"flag": "maybe"})

    def test_bool_invalid_type(self):
        """Test invalid bool type raises."""
        spec = {"flag": {"type": "bool"}}
        with pytest.raises(ValueError, match="must be a boolean"):
            _validate_attrs_from_spec(spec, {"flag": 42})

    def test_enum_invalid_value(self):
        """Test invalid enum value raises."""
        spec = {"color": {"type": "enum", "values": ["red", "green", "blue"]}}
        with pytest.raises(ValueError, match="must be one of"):
            _validate_attrs_from_spec(spec, {"color": "purple"})


class TestBuilderBaseValidateAttrs:
    """Tests for BuilderBase._validate_attrs method."""

    def test_validate_required_attr_missing(self):
        """Test required attribute missing raises."""
        class TestBuilder(BuilderBase):
            _schema = {
                "item": {
                    "attrs": {
                        "name": {"type": "string", "required": True}
                    }
                }
            }

        builder = TestBuilder()
        with pytest.raises(ValueError, match="'name' is required"):
            builder._validate_attrs("item", {}, raise_on_error=True)

    def test_validate_int_conversion_failure(self):
        """Test int conversion failure."""
        class TestBuilder(BuilderBase):
            _schema = {
                "item": {
                    "attrs": {
                        "count": {"type": "int"}
                    }
                }
            }

        builder = TestBuilder()
        errors = builder._validate_attrs("item", {"count": "not_int"}, raise_on_error=False)
        assert any("must be an integer" in e for e in errors)

    def test_validate_int_min_violation(self):
        """Test int min constraint violation."""
        class TestBuilder(BuilderBase):
            _schema = {
                "item": {
                    "attrs": {
                        "count": {"type": "int", "min": 1}
                    }
                }
            }

        builder = TestBuilder()
        errors = builder._validate_attrs("item", {"count": 0}, raise_on_error=False)
        assert any(">= 1" in e for e in errors)

    def test_validate_int_max_violation(self):
        """Test int max constraint violation."""
        class TestBuilder(BuilderBase):
            _schema = {
                "item": {
                    "attrs": {
                        "count": {"type": "int", "max": 10}
                    }
                }
            }

        builder = TestBuilder()
        errors = builder._validate_attrs("item", {"count": 100}, raise_on_error=False)
        assert any("<= 10" in e for e in errors)

    def test_validate_bool_invalid_string(self):
        """Test bool invalid string."""
        class TestBuilder(BuilderBase):
            _schema = {
                "item": {
                    "attrs": {
                        "flag": {"type": "bool"}
                    }
                }
            }

        builder = TestBuilder()
        errors = builder._validate_attrs("item", {"flag": "maybe"}, raise_on_error=False)
        assert any("must be a boolean" in e for e in errors)

    def test_validate_bool_invalid_type(self):
        """Test bool invalid type (not string)."""
        class TestBuilder(BuilderBase):
            _schema = {
                "item": {
                    "attrs": {
                        "flag": {"type": "bool"}
                    }
                }
            }

        builder = TestBuilder()
        errors = builder._validate_attrs("item", {"flag": 42}, raise_on_error=False)
        assert any("must be a boolean" in e for e in errors)

    def test_validate_enum_invalid_value(self):
        """Test enum invalid value."""
        class TestBuilder(BuilderBase):
            _schema = {
                "item": {
                    "attrs": {
                        "color": {"type": "enum", "values": ["red", "green"]}
                    }
                }
            }

        builder = TestBuilder()
        errors = builder._validate_attrs("item", {"color": "blue"}, raise_on_error=False)
        assert any("must be one of" in e for e in errors)

    def test_validate_string_type_accepts_non_string(self):
        """Test string type accepts any value (converted)."""
        class TestBuilder(BuilderBase):
            _schema = {
                "item": {
                    "attrs": {
                        "name": {"type": "string"}
                    }
                }
            }

        builder = TestBuilder()
        # Non-string should be accepted (will be converted)
        errors = builder._validate_attrs("item", {"name": 123}, raise_on_error=False)
        assert errors == []


class TestBuilderBaseResolveRef:
    """Tests for BuilderBase._resolve_ref method."""

    def test_resolve_ref_set_with_mixed_refs(self):
        """Test resolving set with mixed refs and literals."""
        class TestBuilder(BuilderBase):
            @property
            def _ref_items(self):
                return "a, b"

        builder = TestBuilder()
        result = builder._resolve_ref({"=items", "c", "d"})
        assert isinstance(result, set)
        assert "a" in result
        assert "b" in result
        assert "c" in result
        assert "d" in result

    def test_resolve_ref_frozenset(self):
        """Test resolving frozenset with refs."""
        class TestBuilder(BuilderBase):
            @property
            def _ref_items(self):
                return frozenset(["x", "y"])

        builder = TestBuilder()
        result = builder._resolve_ref(frozenset({"=items", "z"}))
        assert isinstance(result, frozenset)
        assert "x" in result
        assert "y" in result
        assert "z" in result

    def test_resolve_ref_comma_with_non_string_result(self):
        """Test resolving comma string when ref returns non-string."""
        class TestBuilder(BuilderBase):
            @property
            def _ref_num(self):
                return 42

        builder = TestBuilder()
        result = builder._resolve_ref("=num, other")
        assert "42" in result
        assert "other" in result

    def test_resolve_ref_not_found_raises(self):
        """Test reference not found raises ValueError."""
        class TestBuilder(BuilderBase):
            pass

        builder = TestBuilder()
        with pytest.raises(ValueError, match="Reference '=nonexistent' not found"):
            builder._resolve_ref("=nonexistent")


class TestBuilderBaseGetattr:
    """Tests for BuilderBase.__getattr__ method."""

    def test_getattr_underscore_raises(self):
        """Test accessing underscore attr raises AttributeError."""
        builder = BuilderBase.__new__(BuilderBase)
        builder._element_tags = {}
        builder._schema = {}
        with pytest.raises(AttributeError, match="has no attribute '_private'"):
            _ = builder._private

    def test_getattr_from_element_tags(self):
        """Test accessing tag from _element_tags."""
        class TestBuilder(BuilderBase):
            @element(tags="foo")
            def bar(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        builder = TestBuilder()
        method = builder.foo
        assert callable(method)

    def test_getattr_not_found_raises(self):
        """Test accessing unknown element raises AttributeError."""
        class TestBuilder(BuilderBase):
            pass

        builder = TestBuilder()
        with pytest.raises(AttributeError, match="has no element 'unknown'"):
            _ = builder.unknown


class TestBuilderBaseMakeSchemaHandler:
    """Tests for BuilderBase._make_schema_handler method."""

    def test_schema_handler_leaf_element(self):
        """Test schema handler for leaf element."""
        class TestBuilder(BuilderBase):
            _schema = {
                "br": {"leaf": True}
            }

        store = TreeStore(builder=TestBuilder())
        node = store.br()
        assert node.value == ""  # leaf elements get empty string

    def test_schema_handler_no_children_spec(self):
        """Test schema handler with no children spec."""
        class TestBuilder(BuilderBase):
            _schema = {
                "item": {}
            }

        builder = TestBuilder()
        handler = builder._make_schema_handler("item", {})
        assert handler._valid_children == frozenset()
        assert handler._child_cardinality == {}


class TestBuilderBaseParseChildrenSpec:
    """Tests for BuilderBase._parse_children_spec method."""

    def test_parse_set_spec(self):
        """Test parsing set spec returns frozenset."""
        class TestBuilder(BuilderBase):
            pass

        builder = TestBuilder()
        result, cardinality = builder._parse_children_spec({"a", "b", "c"})
        assert result == frozenset({"a", "b", "c"})
        assert cardinality == {}


class TestBuilderBaseGetValidationRules:
    """Tests for BuilderBase._get_validation_rules method."""

    def test_get_rules_from_schema(self):
        """Test getting rules from _schema."""
        class TestBuilder(BuilderBase):
            _schema = {
                "container": {"children": "item[1:3]"}
            }

        builder = TestBuilder()
        valid, cardinality = builder._get_validation_rules("container")
        assert "item" in valid
        assert cardinality["item"] == (1, 3)

    def test_get_rules_schema_no_children(self):
        """Test schema element with no children spec."""
        class TestBuilder(BuilderBase):
            _schema = {
                "leaf": {"leaf": True}
            }

        builder = TestBuilder()
        valid, cardinality = builder._get_validation_rules("leaf")
        assert valid == frozenset()
        assert cardinality == {}


class TestBuilderBaseCheck:
    """Tests for BuilderBase.check method."""

    def test_check_invalid_child_tag_no_valid_children(self):
        """Test check with invalid child when no valid children allowed."""
        class TestBuilder(BuilderBase):
            @element(children="")  # No children allowed
            def container(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        store = TreeStore(builder=TestBuilder())
        container = store.container()
        container.set_item("invalid_child", "value")

        errors = TestBuilder().check(container, parent_tag="container")
        assert any("cannot have children" in e for e in errors)

    def test_check_cardinality_min_violation(self):
        """Test check with min cardinality violation."""
        class TestBuilder(BuilderBase):
            @element(children="item[2:]")  # At least 2 required
            def container(self, target, tag, **attr):
                return self.child(target, tag, **attr)

            @element()
            def item(self, target, tag, **attr):
                return self.child(target, tag, value="", **attr)

        store = TreeStore(builder=TestBuilder())
        container = store.container()
        container.item()  # Only 1

        errors = TestBuilder().check(container, parent_tag="container")
        assert any("requires at least 2" in e for e in errors)

    def test_check_cardinality_max_violation(self):
        """Test check with max cardinality violation (using check method directly)."""
        class TestBuilder(BuilderBase):
            @element(children="item[:1]")  # At most 1 allowed
            def container(self, target, tag, **attr):
                return self.child(target, tag, **attr)

            @element()
            def item(self, target, tag, **attr):
                return self.child(target, tag, value="", **attr)

        # Build structure without builder validation - use plain TreeStore
        store = TreeStore()
        container_store = TreeStore()
        from genro_treestore.store.node import TreeStoreNode
        container_node = TreeStoreNode("container_0", {}, value=container_store, tag="container")
        container_store.parent = container_node
        store._insert_node(container_node, trigger=False)

        # Add items directly without triggering validation
        item1 = TreeStoreNode("item_0", {}, value="", tag="item")
        item2 = TreeStoreNode("item_1", {}, value="", tag="item")
        container_store._insert_node(item1, trigger=False)
        container_store._insert_node(item2, trigger=False)

        # Now use check() method to verify the cardinality violation
        errors = TestBuilder().check(container_store, parent_tag="container")
        assert any("allows at most 1" in e for e in errors)

    def test_check_recursive_with_branches(self):
        """Test check recursively validates branches."""
        class TestBuilder(BuilderBase):
            @element(children="inner")
            def outer(self, target, tag, **attr):
                return self.child(target, tag, **attr)

            @element(children="")  # No children for inner
            def inner(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        store = TreeStore(builder=TestBuilder())
        outer = store.outer()
        inner = outer.inner()
        inner.set_item("bad_child", "value")

        errors = TestBuilder().check(outer, parent_tag="outer")
        assert any("cannot have children" in e for e in errors)


class TestElementDecorator:
    """Tests for @element decorator edge cases."""

    def test_element_with_refs_in_children(self):
        """Test element decorator with =refs in children."""
        class TestBuilder(BuilderBase):
            @property
            def _ref_items(self):
                return "a, b, c"

            @element(children="=items")
            def container(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        builder = TestBuilder()
        # The method should have _raw_children_spec stored
        assert hasattr(builder.container, "_raw_children_spec")

    def test_element_with_tuple_children(self):
        """Test element decorator with tuple children."""
        class TestBuilder(BuilderBase):
            @element(children=("a", "b", "c"))
            def container(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        builder = TestBuilder()
        assert hasattr(builder.container, "_valid_children")
        assert "a" in builder.container._valid_children

    def test_element_validates_attrs_at_call_time(self):
        """Test element decorator validates attrs when called."""
        class TestBuilder(BuilderBase):
            @element()
            def item(self, target, tag, count: int = 1, **attr):
                return self.child(target, tag, value="", **attr)

        store = TreeStore(builder=TestBuilder())
        # This should validate and raise for invalid count
        with pytest.raises(ValueError, match="must be an integer"):
            store.item(count="not_a_number")


class TestHtmlBuilder:
    """Tests for HtmlBuilder class."""

    def test_html_builder_unknown_tag_raises(self):
        """Test accessing unknown tag raises AttributeError."""
        builder = HtmlBuilder()
        with pytest.raises(AttributeError, match="is not a valid HTML tag"):
            _ = builder.foobar

    def test_html_builder_underscore_attr_raises(self):
        """Test accessing underscore attr raises."""
        builder = HtmlBuilder()
        with pytest.raises(AttributeError, match="has no attribute"):
            _ = builder._internal


class TestHtmlPage:
    """Tests for HtmlPage class."""

    def test_html_page_creation(self):
        """Test creating an HtmlPage."""
        page = HtmlPage()
        assert page.html is not None
        assert page.head is not None
        assert page.body is not None

    def test_html_page_add_content(self):
        """Test adding content to HtmlPage."""
        page = HtmlPage()
        page.head.title(value="Test Page")
        page.head.meta(charset="utf-8")
        page.body.div(id="main")

        html = page.to_html()
        assert "<!DOCTYPE html>" in html
        assert "<title>Test Page</title>" in html
        assert "<meta charset=\"utf-8\">" in html

    def test_html_page_to_html_with_filename(self, tmp_path):
        """Test saving HtmlPage to file."""
        page = HtmlPage()
        page.head.title(value="Test")
        page.body.p(value="Hello")

        result = page.to_html(filename="test.html", output_dir=str(tmp_path))
        assert result == str(tmp_path / "test.html")
        assert (tmp_path / "test.html").exists()

    def test_html_page_to_html_with_filename_no_dir(self, tmp_path, monkeypatch):
        """Test saving HtmlPage without output_dir uses cwd."""
        monkeypatch.chdir(tmp_path)

        page = HtmlPage()
        page.body.p(value="Test")

        result = page.to_html(filename="output.html")
        assert "output.html" in result
        assert (tmp_path / "output.html").exists()

    def test_html_page_node_to_html_nested(self):
        """Test _node_to_html with nested structure."""
        page = HtmlPage()
        div = page.body.div(id="outer")
        inner = div.div(id="inner")
        inner.p(value="Text")

        html = page.to_html()
        assert '<div id="outer">' in html
        assert '<div id="inner">' in html
        assert "<p>Text</p>" in html

    def test_html_page_node_to_html_void_element(self):
        """Test _node_to_html with void element."""
        page = HtmlPage()
        page.head.meta(charset="utf-8")

        html = page.to_html()
        assert '<meta charset="utf-8">' in html

    def test_html_page_print_tree(self, capsys):
        """Test print_tree method."""
        page = HtmlPage()
        page.head.title(value="Test Title")
        page.body.div(id="main")

        page.print_tree()
        captured = capsys.readouterr()
        assert "HEAD" in captured.out
        assert "BODY" in captured.out
        assert "<title>" in captured.out or "title" in captured.out

    def test_html_page_print_tree_long_value(self, capsys):
        """Test print_tree truncates long values in HEAD section."""
        page = HtmlPage()
        # HEAD section has truncation at 30 chars
        long_text = "A" * 100
        page.head.title(value=long_text)

        page.print_tree()
        captured = capsys.readouterr()
        assert '..."' in captured.out  # Truncated in HEAD


class TestInitSubclass:
    """Tests for __init_subclass__ method."""

    def test_init_subclass_inherits_parent_tags(self):
        """Test that subclass inherits parent's element tags."""
        class ParentBuilder(BuilderBase):
            @element(tags="parent_tag")
            def parent_method(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        class ChildBuilder(ParentBuilder):
            @element(tags="child_tag")
            def child_method(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        assert "parent_tag" in ChildBuilder._element_tags
        assert "child_tag" in ChildBuilder._element_tags

    def test_init_subclass_method_without_explicit_tags(self):
        """Test method decorated with @element but no explicit tags uses method name."""
        class TestBuilder(BuilderBase):
            @element()
            def my_element(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        assert "my_element" in TestBuilder._element_tags


class TestBuilderChild:
    """Tests for BuilderBase.child method."""

    def test_child_with_builder_override(self):
        """Test child with _builder override."""
        class Builder1(BuilderBase):
            @element()
            def container(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        class Builder2(BuilderBase):
            @element()
            def nested(self, target, tag, **attr):
                return self.child(target, tag, **attr)

        store = TreeStore(builder=Builder1())
        container = store.container()

        # Child with different builder
        Builder1().child(container, "nested", _builder=Builder2())

        nested_node = container.get_node("nested_0")
        # The nested branch has Builder2
        assert nested_node.value._builder is not None
        assert isinstance(nested_node.value._builder, Builder2)

    def test_child_auto_label_increments(self):
        """Test auto-labeling increments correctly."""
        class TestBuilder(BuilderBase):
            @element()
            def item(self, target, tag, **attr):
                return self.child(target, tag, value="", **attr)

        store = TreeStore(builder=TestBuilder())
        store.item()
        store.item()
        store.item()

        assert "item_0" in store
        assert "item_1" in store
        assert "item_2" in store
