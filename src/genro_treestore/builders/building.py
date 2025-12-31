# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""BuildingBuilder - Example builder for building/apartment structures.

A didactic example showing how to use @element decorator
for structure validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import BuilderBase
from .decorators import element

if TYPE_CHECKING:
    from ..store import TreeStore
    from ..node import TreeStoreNode


class Building:
    """A building structure with validation.

    This is the "cover" class (like HtmlPage for HTML) that wraps
    a TreeStore with BuildingBuilder and provides a convenient API.

    Example:
        >>> casa = Building(name='Casa Mia')
        >>> floor1 = casa.floor(number=1)
        >>> apt = floor1.apartment(number='1A')
        >>> kitchen = apt.kitchen()
        >>> kitchen.fridge(brand='Samsung')
        >>> kitchen.oven()
        >>>
        >>> # Validate the structure
        >>> errors = casa.validate()
        >>> if errors:
        ...     for e in errors:
        ...         print(e)
        >>>
        >>> # Invalid: fridge in dining_room
        >>> dining = apt.dining_room()
        >>> dining.fridge()  # This will be caught by validate()
        >>> errors = casa.validate()
        >>> # ['fridge is not a valid child of dining_room...']
    """

    def __init__(self, name: str = '', **attr):
        """Create a new building.

        Args:
            name: The building name.
            **attr: Additional attributes for the building node.
        """
        from ..store import TreeStore

        self._store = TreeStore(builder=BuildingBuilder())
        self._root = self._store.building(name=name, **attr)

    @property
    def store(self):
        """Access the underlying TreeStore."""
        return self._store

    @property
    def root(self):
        """Access the root building TreeStore."""
        return self._root

    def floor(self, number: int = 0, **attr):
        """Add a floor to the building."""
        return self._root.floor(number=number, **attr)

    def validate(self) -> list[str]:
        """Validate the building structure.

        Returns:
            List of validation error messages (empty if valid).
        """
        return self._store.builder.validate(self._root, parent_tag='building')

    def print_tree(self):
        """Print the building structure for debugging."""
        print("=" * 60)
        print("BUILDING")
        print("=" * 60)
        for path, node in self._root.walk():
            indent = "  " * path.count('.')
            tag = node.tag or node.label
            attrs = ' '.join(f'{k}={v}' for k, v in node.attr.items() if not k.startswith('_'))
            attrs_str = f' ({attrs})' if attrs else ''
            print(f"{indent}{tag}{attrs_str}")


class BuildingBuilder(BuilderBase):
    """Builder for describing building structures.

    Hierarchy:
        building
          └── floor
                └── apartment | corridor | stairs
                      apartment:
                        └── kitchen | bathroom | bedroom | living_room | dining_room
                              kitchen: fridge, oven, sink, table, chair
                              bathroom: toilet, shower, sink
                              bedroom: bed, wardrobe, desk, chair
                              living_room: sofa, tv, table, chair
                              dining_room: table, chair

    Example:
        >>> store = TreeStore(builder=BuildingBuilder())
        >>> building = store.building(name='Casa Mia')
        >>> floor1 = building.floor(number=1)
        >>> apt = floor1.apartment(number='1A')
        >>> kitchen = apt.kitchen()
        >>> kitchen.fridge(brand='Samsung')
        >>> kitchen.oven()
        >>>
        >>> # This would be an error: fridge in dining_room
        >>> dining = apt.dining_room()
        >>> dining.fridge()  # Valid syntax, but validate() will catch it
        >>>
        >>> errors = store.validate()
        >>> # ['fridge is not a valid child of dining_room']
    """

    # === Building level ===

    @element(children=('floor',))
    def building(self, target: TreeStore, name: str = '', **attr) -> TreeStore:
        """Create a building. Can contain only floors."""
        return self.child(target, 'building', value=None, name=name, **attr)

    # === Floor level ===

    @element(children=('apartment', 'corridor', 'stairs'))
    def floor(self, target: TreeStore, number: int = 0, **attr) -> TreeStore:
        """Create a floor. Can contain apartments, corridors, stairs."""
        return self.child(target, 'floor', value=None, number=number, **attr)

    # === Floor elements ===

    @element(children=('kitchen[:1]', 'bathroom[1:]', 'bedroom', 'living_room[:1]', 'dining_room[:1]'))
    def apartment(self, target: TreeStore, number: str = '', **attr) -> TreeStore:
        """Create an apartment. Must have at least 1 bathroom, max 1 kitchen/living/dining."""
        return self.child(target, 'apartment', value=None, number=number, **attr)

    @element()  # No children allowed
    def corridor(self, target: TreeStore, **attr) -> TreeStoreNode:
        """Create a corridor. Leaf element."""
        return self.child(target, 'corridor', value='', **attr)

    @element()  # No children allowed
    def stairs(self, target: TreeStore, **attr) -> TreeStoreNode:
        """Create stairs. Leaf element."""
        return self.child(target, 'stairs', value='', **attr)

    # === Rooms ===

    @element(children=('fridge[:1]', 'oven[:2]', 'sink[:1]', 'table', 'chair'))
    def kitchen(self, target: TreeStore, **attr) -> TreeStore:
        """Create a kitchen. Max 1 fridge, max 2 ovens, max 1 sink."""
        return self.child(target, 'kitchen', value=None, **attr)

    @element(children=('toilet[:1]', 'shower[:1]', 'sink[:1]'))
    def bathroom(self, target: TreeStore, **attr) -> TreeStore:
        """Create a bathroom. Max 1 of each fixture."""
        return self.child(target, 'bathroom', value=None, **attr)

    @element(children=('bed', 'wardrobe', 'desk', 'chair'))
    def bedroom(self, target: TreeStore, **attr) -> TreeStore:
        """Create a bedroom. Can contain bedroom furniture."""
        return self.child(target, 'bedroom', value=None, **attr)

    @element(children=('sofa', 'tv', 'table', 'chair'))
    def living_room(self, target: TreeStore, **attr) -> TreeStore:
        """Create a living room. Can contain living room furniture."""
        return self.child(target, 'living_room', value=None, **attr)

    @element(children=('table', 'chair'))
    def dining_room(self, target: TreeStore, **attr) -> TreeStore:
        """Create a dining room. Can contain dining furniture."""
        return self.child(target, 'dining_room', value=None, **attr)

    # === Appliances and fixtures (leaf elements) ===

    @element()
    def fridge(self, target: TreeStore, brand: str = '', **attr) -> TreeStoreNode:
        """Create a fridge. Leaf element."""
        return self.child(target, 'fridge', value='', brand=brand, **attr)

    @element()
    def oven(self, target: TreeStore, **attr) -> TreeStoreNode:
        """Create an oven. Leaf element."""
        return self.child(target, 'oven', value='', **attr)

    @element()
    def sink(self, target: TreeStore, **attr) -> TreeStoreNode:
        """Create a sink. Leaf element."""
        return self.child(target, 'sink', value='', **attr)

    @element()
    def toilet(self, target: TreeStore, **attr) -> TreeStoreNode:
        """Create a toilet. Leaf element."""
        return self.child(target, 'toilet', value='', **attr)

    @element()
    def shower(self, target: TreeStore, **attr) -> TreeStoreNode:
        """Create a shower. Leaf element."""
        return self.child(target, 'shower', value='', **attr)

    # === Furniture (leaf elements) ===

    @element()
    def bed(self, target: TreeStore, **attr) -> TreeStoreNode:
        """Create a bed. Leaf element."""
        return self.child(target, 'bed', value='', **attr)

    @element()
    def wardrobe(self, target: TreeStore, **attr) -> TreeStoreNode:
        """Create a wardrobe. Leaf element."""
        return self.child(target, 'wardrobe', value='', **attr)

    @element()
    def desk(self, target: TreeStore, **attr) -> TreeStoreNode:
        """Create a desk. Leaf element."""
        return self.child(target, 'desk', value='', **attr)

    @element()
    def table(self, target: TreeStore, **attr) -> TreeStoreNode:
        """Create a table. Leaf element."""
        return self.child(target, 'table', value='', **attr)

    @element()
    def chair(self, target: TreeStore, **attr) -> TreeStoreNode:
        """Create a chair. Leaf element."""
        return self.child(target, 'chair', value='', **attr)

    @element()
    def sofa(self, target: TreeStore, **attr) -> TreeStoreNode:
        """Create a sofa. Leaf element."""
        return self.child(target, 'sofa', value='', **attr)

    @element()
    def tv(self, target: TreeStore, **attr) -> TreeStoreNode:
        """Create a TV. Leaf element."""
        return self.child(target, 'tv', value='', **attr)
