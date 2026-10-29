"""Central, league-independent derivation logic (Layer 4 of the data model, ADR-055).

``models/`` holds the versioned, immutable models selected per league season; ``ranking``
holds the unversioned order statistics. Nothing in this package reads files, the network,
the clock or league configuration.
"""
