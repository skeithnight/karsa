# Sprint 08 Implementation Plan

## Objective
Transition from architecture blueprinting to physical implementation by establishing the foundational data substrate: the WP-24.5 Institutional Memory Platform.

## Scope
- Base API and Database integration for WP-24.5.
- Implementation of the `ArtifactCatalog` and `ImmutableSnapshot` aggregates.
- Basic Schema Registry to enforce JSON-schema validation on payloads.
- Postgres storage engine for metadata and S3/Blob storage abstractions for payloads.

## Out-of-Scope
- Advanced Decision Replay artifact bundling.
- Knowledge Projection Layer (WP-21 integration).
- Thesis Engine, Allocation Engine, and Portfolio Engine logic.
- Complex garbage collection / archival background workers.

## Deliverables
1. `ArtifactRegistry` HTTP/gRPC API.
2. `ArtifactSchemaRegistry` implementation with basic validation.
3. Postgres migrations for `snapshots_metadata`, `snapshot_lineage`, and `schemas`.
4. Storage interface and local filesystem/mock S3 implementation for Blobs.
5. Emitting `ArtifactPublishedEvent` to a mock or local Kafka instance.

## Acceptance Criteria
- System can accept an arbitrary JSON payload and a Schema ID.
- System rejects payloads that fail schema validation.
- System persists the payload hash and metadata to Postgres.
- System stores the actual JSON payload to blob storage.
- System correctly resolves simple `DERIVED_FROM` lineage queries.
- Architecture completely respects the frozen boundaries defined in ADR-010.

## Implementation Order
1. **Work Package 1**: Database schema migrations and interface definitions.
2. **Work Package 2**: Schema Registry service and validation logic.
3. **Work Package 3**: Blob storage and metadata persistence adapters.
4. **Work Package 4**: Core API endpoints (Publish, Get, Search by Lineage).

## Testing Strategy
- **Unit Tests**: Cryptographic hashing logic, schema validation checks.
- **Integration Tests**: Dockerized Postgres + LocalStack (or local mock) ensuring metadata and blob writes are transactionally consistent.
- **Contract Tests**: Mock APIs for future WP-25 consumption.

## Documentation Updates
- Update `docs/architecture/` with any minor implementation notes or API swagger definitions.

---

## Work Package Breakdown

### Work Package 1: Persistence Layer Foundation
- **Description**: Define the database schema and storage interfaces for the Institutional Memory Platform. Set up SQL migrations for metadata, lineage, and schemas. Define the abstract interface for Blob Storage.
- **Dependencies**: None.
- **Estimated Complexity**: Low (Standard CRUD and DB init).
- **Acceptance Criteria**: Migrations run cleanly; repository interfaces defined.

### Work Package 2: Schema Registry & Validation
- **Description**: Implement the `ArtifactSchemaRegistry`. Create logic to register new JSON schemas and validate incoming artifact payloads against them before persistence.
- **Dependencies**: Work Package 1.
- **Estimated Complexity**: Medium.
- **Acceptance Criteria**: Service rejects invalid JSON payloads and accepts valid ones based on registered schemas.

### Work Package 3: Snapshot Creation & Blob Storage
- **Description**: Implement the `ImmutableSnapshot` aggregate logic. Create the service that calculates the SHA-256 hash of the payload, writes the payload to the Blob Storage adapter, and writes the metadata to the Postgres repository.
- **Dependencies**: Work Packages 1 and 2.
- **Estimated Complexity**: Medium.
- **Acceptance Criteria**: Payloads are consistently hashed and stored in both blob and relational layers.

### Work Package 4: Core API & Event Publishing
- **Description**: Expose the HTTP/gRPC endpoints for publishing and retrieving artifacts. Implement the event publisher to emit `ArtifactPublishedEvent` upon successful snapshot creation.
- **Dependencies**: Work Package 3.
- **Estimated Complexity**: Medium.
- **Acceptance Criteria**: External clients can successfully hit the API to publish an artifact, and the system emits the corresponding event.

---

## Recommended First Implementation Target
**Work Package 1 & 2: Schema Registry and Metadata Persistence**

**Selection Criteria Met**:
- **Highest architectural leverage**: Every other engine (WP-25, WP-26, WP-18) needs to write artifacts. Building the registry and storage mechanism first unblocks all downstream observability.
- **Lowest implementation risk**: This is a standard metadata + blob storage pattern. It contains no complex financial algorithms or multi-agent execution loops.
- **Smallest vertical slice**: A simple HTTP API that validates a JSON payload and writes a database row provides immediate end-to-end value.