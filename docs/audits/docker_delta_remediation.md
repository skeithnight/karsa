# Docker Delta Remediation

## 1. Before
The `docker-compose.yml` file contained an unauthorized modification that mapped the internal `postgres` container port `5432` to the host machine.
```yaml
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: karsa
      POSTGRES_PASSWORD: karsa_password
      POSTGRES_DB: karsa_db
    ports:
      - "5432:5432"
    healthcheck:
```

## 2. After
The `ports` array was entirely removed, restoring the `postgres` container to its strict internal network topology.
```yaml
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: karsa
      POSTGRES_PASSWORD: karsa_password
      POSTGRES_DB: karsa_db
    healthcheck:
```

## 3. Reason
Integration testing locally bypassed the container network by modifying the infrastructure configuration. This violates the `ARCHITECTURE_FROZEN_FINAL` constraints prohibiting speculative infrastructure drift or undocumented modifications.

## 4. Architecture Impact
By reverting this change, the `postgres` database is once again securely isolated from the host machine. Tests requiring database access must be orchestrated inside the container network (e.g. via `docker-compose exec`).

## 5. Verification Evidence
Inspection of `docker-compose.yml` confirms the absence of `ports` configuration under the `postgres` service. `DOCKER_DELTA_REMEDIATED`.
