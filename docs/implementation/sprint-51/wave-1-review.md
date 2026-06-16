# Wave-1 Foundation Hardening Review

## 1. Executive Summary
The Wave-1 Foundation implementation has successfully scaffolded the Next.js `karsa-web` frontend. However, a rigorous hardening review reveals that the initial `create-next-app` defaults are insufficient for robust production deployment without minor adjustments. The current state relies heavily on `legacy-peer-deps` to bypass structural React 19 incompatibilities with `Tremor`, and the `next.config.ts` requires further configuration to guarantee a flawless static export. The foundation is fundamentally sound, but targeted remediations are required before authorizing progression to Wave 2.

## 2. React/Tremor Compatibility Review
1. **Why was React 19 selected?**
   React 19.2.4 was selected automatically by the `npx create-next-app@latest` tooling, which provisions the newest Next.js 16 environment requiring React 19 defaults.
2. **Is Tremor officially compatible with React 19?**
   **No.** `@tremor/react` currently enforces a peer dependency on `react@"^18.0.0"`. It also shares conflicting `date-fns` peer dependencies with `@base-ui/react`.
3. **Is the use of legacy-peer-deps required?**
   **Yes.** Without `legacy-peer-deps=true` in the `.npmrc`, `npm install` structurally fails during dependency resolution.
4. **Can legacy-peer-deps be removed?**
   **No.** It cannot be removed until Tremor natively updates its `package.json` to tolerate React 19.
5. **What risks remain?**
   Using Tremor (built for React 18) within a React 19 concurrent rendering environment creates a minor risk of strict-mode hydration mismatches and deprecated hook warnings (e.g., `useRef` modifications). 

## 3. Next.js Static Export Review
**Current Configuration:**
```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export"
};

export default nextConfig;
```
**Static Export Readiness Assessment:**
While `output: "export"` is present, it is not fully hardened for a zero-Node Nginx deployment. 
* **`trailingSlash`**: Unspecified. Must be set to `true` so Nginx can resolve `/route/index.html` easily.
* **`images.unoptimized`**: Unspecified. Next.js's native `<Image>` component will break during static export without this, as it relies on a Node.js image optimization API.

## 4. Dependency Health Review
| Dependency | Version | Purpose | Risk | Replacement Risk | Compatibility Risk |
|---|---|---|---|---|---|
| `next` | 16.2.9 | Core Framework | Low | High | None |
| `react` | 19.2.4 | UI Engine | Low | High | Medium (with Tremor) |
| `@tremor/react` | ^3.18.7 | BI Dashboards | Medium | Low | High (React 19 Peer Conflict) |
| `ag-grid-react` | ^35.3.1 | Data Tables | Low | High | None |
| `@tanstack/react-query`| ^5.101.0| Async State | Low | Medium | None |
| `zustand` | ^5.0.14 | Global State | Low | Low | None |
| `shadcn` | ^4.11.0 | Component CLI | Low | Low | Medium (date-fns conflict) |

* **Peer Dependency Conflicts**: Heavy collisions between `@tremor/react`, `@base-ui/react`, and `react-day-picker` regarding `date-fns` versions (v3 vs v4). Suppressed via `.npmrc`.

## 5. Build Reproducibility Review
* **`npm ci`**: Verified. Runs safely given the `package-lock.json` and `.npmrc` constraints.
* **`npm run lint`**: Verified. Standard ESLint 9 configuration parses successfully.
* **`npm run build`**: Verified. Generates valid `out/` directory.
* **Hidden Dependencies**: None identified. Configuration is cleanly isolated to the repository tree.

## 6. Container Readiness Review
* **Static Export Output**: Present (`out/` is successfully compiled).
* **Nginx Compatibility**: Strong, but requires `trailingSlash` remediation to prevent 404 routing errors on direct URL access.
* **Runtime Requirements**: Zero Node.js runtime required. Fully decoupled.
* **Docker Compatibility**: High. The `out/` directory can be mapped or copied directly into an `nginx:alpine` image.

## 7. Foundation Risk Register
| Risk ID | Description | Severity | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|---|
| FR-01 | React 19 / Tremor Peer Conflict | Medium | Certain | `npm install` failure | Enforce `legacy-peer-deps=true` via `.npmrc` | MITIGATED |
| FR-02 | Next.js Image Optimization Crash | High | Medium | Build failure if `<Image>` used | Set `images.unoptimized: true` | PENDING |
| FR-03 | Nginx Deep-Link 404s | Medium | High | Operator sees blank page on refresh | Set `trailingSlash: true` | PENDING |

## 8. Required Remediations
### Remediation 1: Harden Static Export
* **File**: `next.config.ts`
* **Current State**: 
  ```typescript
  const nextConfig: NextConfig = {
    output: "export"
  };
  ```
* **Required State**:
  ```typescript
  const nextConfig: NextConfig = {
    output: "export",
    trailingSlash: true,
    images: {
      unoptimized: true
    }
  };
  ```
* **Reason**: Next.js requires `unoptimized` images for purely static builds. `trailingSlash` forces strict directory generation (`/route/index.html`), which is native to Nginx configurations.
* **Risk Reduction**: Eliminates FR-02 and FR-03.

## 9. Final Verdict
**WAVE_1_APPROVED_WITH_REMEDIATIONS**

The foundation is fundamentally viable. Once the `next.config.ts` remediations are applied, Wave-2 (DTO generation) may commence.
