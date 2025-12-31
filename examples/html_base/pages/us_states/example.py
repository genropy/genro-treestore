# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Example page: US States list using for loops."""

from pathlib import Path
import sys

# Add parent to path for imports when running directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from examples.html_base import HtmlPage


# US States data: (code, name, capital)
US_STATES = [
    ('AL', 'Alabama', 'Montgomery'),
    ('AK', 'Alaska', 'Juneau'),
    ('AZ', 'Arizona', 'Phoenix'),
    ('AR', 'Arkansas', 'Little Rock'),
    ('CA', 'California', 'Sacramento'),
    ('CO', 'Colorado', 'Denver'),
    ('CT', 'Connecticut', 'Hartford'),
    ('DE', 'Delaware', 'Dover'),
    ('FL', 'Florida', 'Tallahassee'),
    ('GA', 'Georgia', 'Atlanta'),
    ('HI', 'Hawaii', 'Honolulu'),
    ('ID', 'Idaho', 'Boise'),
    ('IL', 'Illinois', 'Springfield'),
    ('IN', 'Indiana', 'Indianapolis'),
    ('IA', 'Iowa', 'Des Moines'),
    ('KS', 'Kansas', 'Topeka'),
    ('KY', 'Kentucky', 'Frankfort'),
    ('LA', 'Louisiana', 'Baton Rouge'),
    ('ME', 'Maine', 'Augusta'),
    ('MD', 'Maryland', 'Annapolis'),
    ('MA', 'Massachusetts', 'Boston'),
    ('MI', 'Michigan', 'Lansing'),
    ('MN', 'Minnesota', 'Saint Paul'),
    ('MS', 'Mississippi', 'Jackson'),
    ('MO', 'Missouri', 'Jefferson City'),
    ('MT', 'Montana', 'Helena'),
    ('NE', 'Nebraska', 'Lincoln'),
    ('NV', 'Nevada', 'Carson City'),
    ('NH', 'New Hampshire', 'Concord'),
    ('NJ', 'New Jersey', 'Trenton'),
    ('NM', 'New Mexico', 'Santa Fe'),
    ('NY', 'New York', 'Albany'),
    ('NC', 'North Carolina', 'Raleigh'),
    ('ND', 'North Dakota', 'Bismarck'),
    ('OH', 'Ohio', 'Columbus'),
    ('OK', 'Oklahoma', 'Oklahoma City'),
    ('OR', 'Oregon', 'Salem'),
    ('PA', 'Pennsylvania', 'Harrisburg'),
    ('RI', 'Rhode Island', 'Providence'),
    ('SC', 'South Carolina', 'Columbia'),
    ('SD', 'South Dakota', 'Pierre'),
    ('TN', 'Tennessee', 'Nashville'),
    ('TX', 'Texas', 'Austin'),
    ('UT', 'Utah', 'Salt Lake City'),
    ('VT', 'Vermont', 'Montpelier'),
    ('VA', 'Virginia', 'Richmond'),
    ('WA', 'Washington', 'Olympia'),
    ('WV', 'West Virginia', 'Charleston'),
    ('WI', 'Wisconsin', 'Madison'),
    ('WY', 'Wyoming', 'Cheyenne'),
]


class USStatesPage(HtmlPage):
    """Page displaying US states in a table and grouped lists."""

    def build(self):
        """Build the page content."""
        self.build_head()
        self.build_body()
        return self

    def build_head(self):
        """Build the <head> content."""
        self.head.meta(charset='utf-8')
        self.head.title(value='US States')
        self.head.style(value='''
    body { font-family: sans-serif; margin: 20px; }
    h1 { color: #333; }
    h2 { color: #666; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
    h3 { color: #888; }
    table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
    th { background: #f5f5f5; }
    tr:nth-child(even) { background: #fafafa; }
    ul { list-style: none; padding: 0; }
    li { padding: 4px 0; border-bottom: 1px dotted #ddd; }
    li:last-child { border-bottom: none; }
        ''')

    def build_body(self):
        """Build the <body> content."""
        container = self.body.div(id='container')
        container.h1(value='United States of America')
        self.build_states_table(container)
        self.build_states_by_letter(container)

    def build_states_table(self, parent):
        """Build a table with all states using for loop."""
        parent.h2(value='All States')
        table = parent.table()

        # Header
        thead = table.thead()
        tr = thead.tr()
        tr.th(value='Code')
        tr.th(value='State')
        tr.th(value='Capital')

        # Body - iterate over all states
        tbody = table.tbody()
        for code, name, capital in US_STATES:
            row = tbody.tr()
            row.td(value=code)
            row.td(value=name)
            row.td(value=capital)

    def build_states_by_letter(self, parent):
        """Build lists of states grouped by first letter."""
        parent.h2(value='States by First Letter')

        # Group states by first letter
        groups = {}
        for code, name, capital in US_STATES:
            letter = name[0]
            if letter not in groups:
                groups[letter] = []
            groups[letter].append((code, name, capital))

        # Build a list for each letter group
        for letter in sorted(groups.keys()):
            states = groups[letter]
            parent.h3(value=f'Letter {letter}')
            ul = parent.ul()
            for code, name, capital in states:
                ul.li(value=f'{name} ({code}) - Capital: {capital}')


if __name__ == '__main__':
    page = USStatesPage()
    page.build()
    page.print_tree()

    # Generate and save HTML in same directory as this script
    output_dir = Path(__file__).parent
    output_path = page.to_html('us_states.html', output_dir=output_dir)
    print(f"\nHTML saved to: {output_path}")
