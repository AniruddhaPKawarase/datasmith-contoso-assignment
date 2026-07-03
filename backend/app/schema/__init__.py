"""Schema intelligence module.

- ``metadata`` : immutable dataclasses for tables/columns/FKs
- ``introspection`` : pull schema + Odoo semantic descriptions from PG
- ``domains`` : domain-to-schema mapping for the 5 agents
- ``glossary`` : business glossary (term -> SQL fragment)
- ``joins`` : FK graph + shortest-path discovery
- ``retrieval`` : CSR-RAG hybrid retrieval (Phase 4)
"""

from app.schema.domains import (
    Domain,
    DomainCoverageReport,
    DomainMapping,
    DomainSpec,
    SharedGroup,
    load_domain_mapping,
)
from app.schema.glossary import (
    AmbiguousTerm,
    Glossary,
    GlossaryEntry,
    load_glossary,
)
from app.schema.introspection import SchemaIntrospector
from app.schema.joins import JoinGraph, JoinPath, JoinStep
from app.schema.metadata import (
    Column,
    ForeignKey,
    SchemaMetadata,
    Table,
)
from app.schema.search import SchemaSearch, TableMatch

__all__ = [
    "AmbiguousTerm",
    "Column",
    "Domain",
    "DomainCoverageReport",
    "DomainMapping",
    "DomainSpec",
    "ForeignKey",
    "Glossary",
    "GlossaryEntry",
    "JoinGraph",
    "JoinPath",
    "JoinStep",
    "SchemaIntrospector",
    "SchemaMetadata",
    "SchemaSearch",
    "SharedGroup",
    "Table",
    "TableMatch",
    "load_domain_mapping",
    "load_glossary",
]
