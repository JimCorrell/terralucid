initial readme 

## Data foundation

See [architecture](docs/architecture.md), [source audit](research/maine-sources/README.md),
[ingestion plan](docs/ingestion-plan.md), and [Supabase staging setup](docs/supabase-staging.md).

The [coverage and identifier audit](research/maine-coverage/README.md) records source presence, key conflicts and assessment-join limits.

[Bounded source ingestion](research/maine-ingestion/README.md) now connects source records
to the [findings register](docs/findings-register.md) for continuing follow-up.

The [first conflict investigation](research/conflict-investigation/README.md) traces Sweden, Alfred and smaller name differences to spatial and assessment evidence.

[Municipal corroboration and proposed corrections](research/municipal-corroboration/README.md) add dated map evidence, explicit exception holds, and a native-ring diagnosis.

The [reviewed correction layer](docs/correction-layer.md) makes snapshot-specific
municipality and identifier interpretations usable alongside their raw evidence,
with withdrawal history and unresolved holds preserved.

The [bounded zoning pilot](research/zoning-ingestion/README.md) adds source-preserving
zoning features and reproducible screening with explicit municipal coverage gaps,
geometry defects and correction-event dependencies.

[Osborn FEMA source qualification](research/osborn-fema/README.md) connects current
flood-zone evidence to the 2016 study and 2024 map revision, preserving geometry
issues and legal-adoption unknowns before parcel screening.

The [bounded wetlands load](research/wetlands-load/README.md) makes the 669-record
Osborn NWI service inventory queryable, retaining source variants, reviewed
classifications, availability dependencies and imagery/legal qualifications.

The [Piscataquis County inventory and evaluation](research/piscataquis-ingestion/README.md)
expands parcels, LUPC zoning, and NWI package wetlands together, retaining source
geometry holds, jurisdiction coverage and imagery-age qualifications.

The [county geometry correction layer](docs/county-geometry-corrections.md) exposes
three reviewed interpretations alongside original evidence, with withdrawal
history and dependency checks for future county analysis.
