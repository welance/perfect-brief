# NOTES — Phase 0 recon decisions (r001-15 / perfect-brief)
**Deploy path.** Dual-home: `github.com/welance/perfect-brief` is the public
OSS face (repo + Pages). Deploys run from a GitLab twin
`gitlab.com/welance/r001-15-perfect-brief` on the shared CI template
(`welance/platform/pipelines/templates/pipeline/git-flow`, `node.yml` — its
docker-build is generic). Kept in sync by pushing to both remotes. GitOps: CI
builds the image, commits an `image.tag` bump into
`platform/tenants/welance-prod` (branch `develop`); ArgoCD reconciles.

**Registry.** `registry.gitlab.com/welance/r001-15-perfect-brief` (GitLab
container registry; pull secret `regcred`, chart default).

**Ingress/DNS.** New tenant `production/r001-15-production/` in the
`welance-prod` tenants repo (via MR): chart `charts/node`, namespace
`r001-15-production`, class `welance-production`, nodeSelector
`welance/environment: production`. Web ingress
`r001-15.production.welance.space` (external-dns auto-creates). Public domain
via `ingresses.live`: `briefs.welance.com`, TLS `cloudflare-tls` — the
`docs.otto.welance.com` (p007-20) pattern. external-dns filters to
`welance.space` only → `briefs.welance.com` is a manual Cloudflare proxied
CNAME to the prod LB. Redis: chart sidecar `redis.enabled: true` (ephemeral).
Probes: liveness/readiness `httpGet /v1/healthz` (override chart default).

**Secrets.** 1Password operator: vault `DevOps`, item `r001-15_env.production`;
in `env.yaml`, `PB_ANTHROPIC_API_KEY` stays the literal
`INJECTED-FROM-DevOpsVault-BY-1PASSWORD-OPERATOR` placeholder;
`deployment.onepassword.enabled: true`. No plaintext secrets in git.

**Pages.** GitHub Pages via Actions workflow (upload-pages-artifact of `site/`,
no `/docs` rename). Phase 5 directory-issue link: (pending).
