# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Example page: Shopping list and contacts table."""

from pathlib import Path
import sys

# Add parent to path for imports when running directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from examples.html_base import HtmlPage


class ShoppingAndContactsPage(HtmlPage):
    """Example page with shopping list and contacts table."""

    def build(self):
        """Build the page content."""
        self.build_head()
        self.build_body()
        return self

    def build_head(self):
        """Build the <head> content."""
        self.head.meta(charset='utf-8')
        self.head.title(value='HTML Base Example')
        self.head.style(value='''
    body { font-family: sans-serif; margin: 20px; }
    #header { background: #f0f0f0; padding: 10px; }
    #content { margin: 20px 0; }
    #footer { background: #f0f0f0; padding: 10px; font-size: 0.9em; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
    th { background: #f5f5f5; }
    ul { margin: 10px 0; }
        ''')

    def build_body(self):
        """Build the <body> content."""
        page = self.body.div(id='page')
        self.build_header(page)
        self.build_content(page)
        self.build_footer(page)

    def build_header(self, parent):
        """Build the page header."""
        header = parent.div(id='header')
        header.h1(value='Welcome')
        header.h2(value='Page subtitle')

    def build_content(self, parent):
        """Build the main content."""
        content = parent.div(id='content')
        self.build_shopping_list(content)
        self.build_contacts_table(content)

    def build_shopping_list(self, parent):
        """Build the shopping list."""
        parent.h3(value='Shopping List')
        lista = parent.ul()
        lista.li(value='Bread')
        lista.li(value='Milk')
        lista.li(value='Eggs')

    def build_contacts_table(self, parent):
        """Build the contacts table."""
        parent.h3(value='Contacts')
        table = parent.table()
        self.build_table_header(table)
        self.build_table_body(table)

    def build_table_header(self, table):
        """Build the table header."""
        thead = table.thead()
        tr = thead.tr()
        tr.th(value='Name')
        tr.th(value='Email')
        tr.th(value='Phone')

    def build_table_body(self, table):
        """Build the table body."""
        tbody = table.tbody()
        self.build_table_row(tbody, 'John Smith', 'john@example.com', '555-1234567')
        self.build_table_row(tbody, 'Jane Doe', 'jane@example.com', '555-7654321')

    def build_table_row(self, tbody, name, email, phone):
        """Build a table row."""
        row = tbody.tr()
        row.td(value=name)
        row.td(value=email)
        row.td(value=phone)

    def build_footer(self, parent):
        """Build the page footer."""
        footer = parent.div(id='footer')
        footer.span(value='© 2025 - All rights reserved')


if __name__ == '__main__':
    page = ShoppingAndContactsPage()
    page.build()
    page.print_tree()

    # Generate and save HTML in same directory as this script
    output_dir = Path(__file__).parent
    output_path = page.to_html('example.html', output_dir=output_dir)
    print(f"\nHTML saved to: {output_path}")
