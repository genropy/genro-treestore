# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Italian Electronic Invoice Example - FatturaPA using XsdBuilder.

Demonstrates using XsdBuilder to create a builder from the official
FatturaPA XSD schema and generate valid electronic invoices.

The XSD schema is downloaded from the Italian government repository.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

from genro_treestore import TreeStore
from genro_treestore.builders.xsd import XsdBuilder

# FatturaPA XSD URL (v1.2.3)
XSD_URL = 'https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.4/Schema_VFPA12_V1.2.3.xsd'
XSD_CACHE = Path(__file__).parent / 'Schema_VFPA12_V1.2.3.xsd'


def get_xsd_content() -> str:
    """Get XSD content, downloading if not cached."""
    if XSD_CACHE.exists():
        return XSD_CACHE.read_text()

    print(f"Downloading FatturaPA XSD from {XSD_URL}...")
    with urllib.request.urlopen(XSD_URL) as response:
        content = response.read().decode('utf-8')

    XSD_CACHE.write_text(content)
    print(f"Cached to {XSD_CACHE}")
    return content


def create_invoice_builder() -> XsdBuilder:
    """Create XsdBuilder from FatturaPA schema."""
    xsd_content = get_xsd_content()
    schema = TreeStore.from_xml(xsd_content)
    return XsdBuilder(schema)


def example_simple_invoice():
    """Create a simple invoice structure."""
    builder = create_invoice_builder()

    print(f"\nAvailable elements: {len(builder.elements)}")
    print(f"Sample elements: {list(builder.elements)[:10]}...")

    # Create invoice
    invoice = TreeStore(builder=builder)

    # Root element
    fe = invoice.FatturaElettronica(versione='FPR12')

    # Header
    header = fe.FatturaElettronicaHeader()

    # DatiTrasmissione (transmission data)
    dati_trasm = header.DatiTrasmissione()
    id_trasm = dati_trasm.IdTrasmittente()
    id_trasm.IdPaese(value='IT')
    id_trasm.IdCodice(value='01234567890')
    dati_trasm.ProgressivoInvio(value='00001')
    dati_trasm.FormatoTrasmissione(value='FPR12')
    dati_trasm.CodiceDestinatario(value='0000000')

    # CedentePrestatore (seller)
    seller = header.CedentePrestatore()
    seller_data = seller.DatiAnagrafici()
    seller_vat = seller_data.IdFiscaleIVA()
    seller_vat.IdPaese(value='IT')
    seller_vat.IdCodice(value='01234567890')
    seller_name = seller_data.Anagrafica()
    seller_name.Denominazione(value='Softwell S.r.l.')
    seller_data.RegimeFiscale(value='RF01')

    seller_addr = seller.Sede()
    seller_addr.Indirizzo(value='Via Roma 1')
    seller_addr.CAP(value='00100')
    seller_addr.Comune(value='Roma')
    seller_addr.Provincia(value='RM')
    seller_addr.Nazione(value='IT')

    # CessionarioCommittente (buyer)
    buyer = header.CessionarioCommittente()
    buyer_data = buyer.DatiAnagrafici()
    buyer_data.CodiceFiscale(value='RSSMRA80A01H501U')
    buyer_name = buyer_data.Anagrafica()
    buyer_name.Nome(value='Mario')
    buyer_name.Cognome(value='Rossi')

    buyer_addr = buyer.Sede()
    buyer_addr.Indirizzo(value='Via Milano 10')
    buyer_addr.CAP(value='20100')
    buyer_addr.Comune(value='Milano')
    buyer_addr.Provincia(value='MI')
    buyer_addr.Nazione(value='IT')

    # Body
    body = fe.FatturaElettronicaBody()

    # DatiGenerali (general data)
    general = body.DatiGenerali()
    doc_data = general.DatiGeneraliDocumento()
    doc_data.TipoDocumento(value='TD01')
    doc_data.Divisa(value='EUR')
    doc_data.Data(value='2025-01-01')
    doc_data.Numero(value='1')

    # DatiBeniServizi (goods/services)
    goods = body.DatiBeniServizi()

    # Line item
    line = goods.DettaglioLinee()
    line.NumeroLinea(value='1')
    line.Descrizione(value='Consulting service')
    line.Quantita(value='1.00')
    line.PrezzoUnitario(value='1000.00')
    line.PrezzoTotale(value='1000.00')
    line.AliquotaIVA(value='22.00')

    # Summary
    summary = goods.DatiRiepilogo()
    summary.AliquotaIVA(value='22.00')
    summary.ImponibileImporto(value='1000.00')
    summary.Imposta(value='220.00')
    summary.EsigibilitaIVA(value='I')

    # Payment
    payment = body.DatiPagamento()
    payment.CondizioniPagamento(value='TP02')
    payment_detail = payment.DettaglioPagamento()
    payment_detail.ModalitaPagamento(value='MP05')
    payment_detail.ImportoPagamento(value='1220.00')

    return invoice


def show_structure(store: TreeStore, indent: int = 0):
    """Display TreeStore structure."""
    for node in store.nodes():
        prefix = '  ' * indent
        tag = node.tag or node.label
        if node.is_branch:
            print(f'{prefix}<{tag}>')
            show_structure(node.value, indent + 1)
            print(f'{prefix}</{tag}>')
        else:
            print(f'{prefix}<{tag}>{node.value}</{tag}>')


if __name__ == '__main__':
    print("=" * 60)
    print("Italian Electronic Invoice (FatturaPA) - XsdBuilder Example")
    print("=" * 60)

    invoice = example_simple_invoice()

    print("\nInvoice structure:")
    print("-" * 60)
    show_structure(invoice)
