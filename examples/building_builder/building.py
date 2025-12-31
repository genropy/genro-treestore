# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""BuildingBuilder - Example builder for building/apartment structures.

A didactic example showing how to use @element decorator for:
- Structure validation with check parameter
- Simple elements (single node)
- Complex elements (nested structures created by a single method call)
"""

from __future__ import annotations

from genro_treestore import TreeStore, TreeStoreNode
from genro_treestore.builders import BuilderBase, element


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
        >>> # Check the structure
        >>> errors = casa.check()
        >>> if errors:
        ...     for e in errors:
        ...         print(e)
        >>>
        >>> # Invalid: fridge in dining_room
        >>> dining = apt.dining_room()
        >>> dining.fridge()  # This will be caught by check()
        >>> errors = casa.check()
        >>> # ['fridge is not a valid child of dining_room...']
    """

    def __init__(self, name: str = '', **attr):
        """Create a new building.

        Args:
            name: The building name.
            **attr: Additional attributes for the building node.
        """
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

    def check(self) -> list[str]:
        """Check the building structure.

        Returns:
            List of error messages (empty if valid).
        """
        return self._store.builder.check(self._root, parent_tag='building')

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

    This builder demonstrates two types of elements:

    1. SIMPLE ELEMENTS: Create a single node
       - Most elements (floor, apartment, bed, table, etc.)
       - Return a TreeStore (branch) or TreeStoreNode (leaf)

    2. COMPLEX ELEMENTS: Create a nested structure
       - Example: wardrobe(drawers=4, doors=2) creates:
         wardrobe
           └── chest_of_drawers
           │     └── drawer (x4)
           └── door (x2)
       - A single method call creates multiple nodes
       - Useful for composite structures with internal logic

    Hierarchy:
        building
          └── floor
                └── apartment | corridor | stairs
                      apartment:
                        └── kitchen | bathroom | bedroom | living_room | dining_room
                              kitchen: fridge, oven, sink, table, chair
                              bathroom: toilet, shower, sink
                              bedroom: bed, wardrobe, desk, chair
                                wardrobe (COMPLEX):
                                  └── chest_of_drawers
                                  │     └── drawer (multiple)
                                  └── door (multiple)
                              living_room: sofa, tv, table, chair
                              dining_room: table, chair

    Example:
        >>> store = TreeStore(builder=BuildingBuilder())
        >>> building = store.building(name='Casa Mia')
        >>> floor1 = building.floor(number=1)
        >>> apt = floor1.apartment(number='1A')
        >>>
        >>> # Simple elements
        >>> kitchen = apt.kitchen()
        >>> kitchen.fridge(brand='Samsung')
        >>>
        >>> # Complex element - creates nested structure
        >>> bedroom = apt.bedroom()
        >>> bedroom.wardrobe(drawers=6, doors=3, color='oak')
        >>>
        >>> errors = store.builder.check(building, parent_tag='building')
    """

    # === Building level ===

    @element(check='floor')
    def building(self, target: TreeStore, tag: str, name: str = '', **attr) -> TreeStore:
        """Create a building. Can contain only floors."""
        return self.child(target, tag, value=None, name=name, **attr)

    # === Floor level ===

    @element(check='apartment, corridor, stairs')
    def floor(self, target: TreeStore, tag: str, number: int = 0, **attr) -> TreeStore:
        """Create a floor. Can contain apartments, corridors, stairs."""
        return self.child(target, tag, value=None, number=number, **attr)

    # === Floor elements ===

    @element(check='kitchen[:1], bathroom[1:], bedroom, living_room[:1], dining_room[:1]')
    def apartment(self, target: TreeStore, tag: str, number: str = '', **attr) -> TreeStore:
        """Create an apartment. Must have at least 1 bathroom, max 1 kitchen/living/dining."""
        return self.child(target, tag, value=None, number=number, **attr)

    @element()  # No children allowed
    def corridor(self, target: TreeStore, tag: str, **attr) -> TreeStoreNode:
        """Create a corridor. Leaf element."""
        return self.child(target, tag, value='', **attr)

    @element()  # No children allowed
    def stairs(self, target: TreeStore, tag: str, **attr) -> TreeStoreNode:
        """Create stairs. Leaf element."""
        return self.child(target, tag, value='', **attr)

    # === Rooms ===

    @element(check='fridge[:1], oven[:2], sink[:1], table, chair')
    def kitchen(self, target: TreeStore, tag: str, **attr) -> TreeStore:
        """Create a kitchen. Max 1 fridge, max 2 ovens, max 1 sink."""
        return self.child(target, tag, value=None, **attr)

    @element(check='toilet[:1], shower[:1], sink[:1]')
    def bathroom(self, target: TreeStore, tag: str, **attr) -> TreeStore:
        """Create a bathroom. Max 1 of each fixture."""
        return self.child(target, tag, value=None, **attr)

    @element(check='bed, wardrobe, desk, chair')
    def bedroom(self, target: TreeStore, tag: str, **attr) -> TreeStore:
        """Create a bedroom. Can contain bedroom furniture."""
        return self.child(target, tag, value=None, **attr)

    @element(check='sofa, tv, table, chair')
    def living_room(self, target: TreeStore, tag: str, **attr) -> TreeStore:
        """Create a living room. Can contain living room furniture."""
        return self.child(target, tag, value=None, **attr)

    @element(check='table, chair')
    def dining_room(self, target: TreeStore, tag: str, **attr) -> TreeStore:
        """Create a dining room. Can contain dining furniture."""
        return self.child(target, tag, value=None, **attr)

    # === Appliances and fixtures (leaf elements) ===
    # Using tags parameter to map multiple tags to same method

    @element(tags='fridge, oven, sink, toilet, shower')
    def appliance(self, target: TreeStore, tag: str, **attr) -> TreeStoreNode:
        """Create an appliance/fixture. Leaf element."""
        return self.child(target, tag, value='', **attr)

    # === Simple furniture (leaf elements) ===

    @element(tags='bed, desk, table, chair, sofa, tv')
    def furniture(self, target: TreeStore, tag: str, **attr) -> TreeStoreNode:
        """Create a simple piece of furniture. Leaf element."""
        return self.child(target, tag, value='', **attr)

    # === Complex furniture (nested structures) ===
    # A single method call can create multiple nodes

    @element(check='chest_of_drawers[:1], door')
    def wardrobe(
        self, target: TreeStore, tag: str,
        drawers: int = 4, doors: int = 2, **attr
    ) -> TreeStore:
        """Create a wardrobe with chest of drawers and doors.

        This is an example of a COMPLEX ELEMENT: a single method call
        creates a nested structure with multiple children.

        Args:
            target: The TreeStore to add to.
            tag: The tag name (always 'wardrobe').
            drawers: Number of drawers in the chest (default 4).
            doors: Number of doors (default 2).
            **attr: Additional attributes.

        Returns:
            The wardrobe TreeStore (for potential further customization).

        Example:
            >>> bedroom.wardrobe(drawers=6, doors=3, color='white')
            # Creates:
            # wardrobe (color=white)
            #   └── chest_of_drawers
            #   │     └── drawer (number=1)
            #   │     └── drawer (number=2)
            #   │     └── drawer (number=3)
            #   │     └── drawer (number=4)
            #   │     └── drawer (number=5)
            #   │     └── drawer (number=6)
            #   └── door (number=1)
            #   └── door (number=2)
            #   └── door (number=3)
        """
        wardrobe = self.child(target, tag, value=None, **attr)

        # Create chest of drawers with N drawers
        if drawers > 0:
            chest = wardrobe.chest_of_drawers()
            for i in range(drawers):
                chest.drawer(number=i + 1)

        # Create doors
        for i in range(doors):
            wardrobe.door(number=i + 1)

        return wardrobe

    @element(check='drawer')
    def chest_of_drawers(self, target: TreeStore, tag: str, **attr) -> TreeStore:
        """Create a chest of drawers container."""
        return self.child(target, tag, value=None, **attr)

    @element(tags='drawer, door')
    def wardrobe_part(self, target: TreeStore, tag: str, **attr) -> TreeStoreNode:
        """Create a wardrobe component (drawer or door). Leaf element."""
        return self.child(target, tag, value='', **attr)
