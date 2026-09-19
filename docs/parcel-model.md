# Parcel model (conceptual)

A **parcel** is the stable acquisition subject; a listing is only one possible source about it. This is a conceptual model, not a database schema.

- **Parcel identity:** jurisdiction, township or municipality, map/lot and source identifiers, with crosswalks where identifiers differ.
- **Geometry evidence:** multiple geometries per parcel (assessment GIS, listing sketch, deed-derived reconstruction, recorded survey, field observations), each with source, date, method, confidence, and legal authority. No single polygon silently becomes a surveyed boundary.
- **Findings:** value, unit, evidence state, source reference, retrieval date, method, confidence or uncertainty, and dependency on geometry. VERIFIED means supported by direct authoritative evidence; DERIVED is a reproducible calculation; INFERRED is an analytical conclusion; UNKNOWN needs further evidence.
- **Boundary evidence:** deeds, legal descriptions, recorded plans, monuments, adjoining evidence, discrepancies, boundary confidence, and boundary dependency for the intended use.
- **Access/title:** physical route, road condition and maintenance, legal right or easement, restrictions, and unresolved questions tracked separately.
- **Use feasibility:** terrain, water, soils, zoning, septic/buildability, recreation, remoteness, privacy, and access quality as separate findings.
- **Acquisition workflow:** listings, due-diligence items, evidence requests, field or professional checks, critical unknowns, and offer-readiness status.

A spatial result must identify the geometry and layer versions used. Boundary-sensitive claims such as frontage, adjoining ownership, or a buildable envelope need stronger boundary evidence than broad regional metrics.
