# Week 2: Container Deployment and Operational Requirements

## The Deployment Problem

Getting code onto servers is not deployment. Deployment is running code reliably at scale, in a way that allows you to observe what's happening, detect problems quickly, and recover from failures without losing data or interrupting users.

Traditional deployment (SSH into a server, pull code, restart service) does not scale. A single server fails. Ten servers become unmanageable. Fifty servers become a nightmare. Container orchestration (Kubernetes) solves the automation problem but introduces new operational constraints.

This week is about understanding what deployment systems actually need to do and why certain architectural choices matter.

## Why Kubernetes Is Harder Than It Looks

[Recent research identifies 7 key production challenges teams face with Kubernetes.](https://octopus.com/devops/kubernetes-deployments/kubernetes-in-production/) The most deceptive is this: a deployment can look successful while simultaneously breaking the application.

Kubernetes is telling you three things:
- Pods started (pass): true
- Readiness probes passed (pass): true
- Application is actually working (unknown): ?

The first two are infrastructure facts. The third is user-visible reality. [A successful kubectl rollout status can coincide with a spike in 500 errors, high latency, or critical connection failures.](https://scaleops.com/blog/kubectl-rollout-best-practices-for-production-2025/)

This gap exists because Kubernetes checks only whether your code is running, not whether it's correct.

## Health Checks That Actually Work

Production systems distinguish between two types of failure:

**Readiness**: Can this container accept requests right now?
- Is the database connection ready? 
- Has the configuration loaded?
- Are required dependencies available?

**Liveness**: Should this container be restarted?
- Is the application making progress?
- Has it deadlocked?
- Is it in an unrecoverable state?

[These are not the same thing.](https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-best-practices-setting-up-health-checks-with-readiness-and-liveness-probes/) A failing readiness probe means "remove from load balancer but don't restart." A failing liveness probe means "restart this container."

Most teams configure both probes identically. This causes cascades: temporary issues trigger restarts, which delay startup, failing the readiness probe again. The system looks crashed but actually just slow.

[Documented production deployments recommend different thresholds for each.](https://kubebyexample.com/learning-paths/application-development-kubernetes/lesson-4-customize-deployments-application-2) Measure your application's actual behavior. For a service with 10s startup and occasional 2s hiccups: readiness checks fast (initialDelaySeconds: 15) to remove traffic quickly; liveness checks slowly (initialDelaySeconds: 45) to avoid restart cascades. The numbers come from measurement, not guessing.

## Resource Utilization vs Reliability

[The 2025 Kubernetes Benchmark Report documents that average CPU utilization is 10% and memory utilization is 23%.](https://scaleops.com/blog/the-complete-guide-to-kubernetes-management-in-2025-7-pillars-for-production-scale/) This seems wasteful. But the waste is intentional: it's the cost of reliability.

Resource requests and limits are bets about CPU and memory needs. Bet too low: throttling or eviction. Bet too high: wasted money. Measurement requires production data, which arrives only after deployment. So teams ship conservatively and tune later.

Two autoscalers complicate this:
- HPA (Horizontal Pod Autoscaler) controls the number of pods
- VPA (Vertical Pod Autoscaler) controls resource requests per pod

[Running both in automatic mode creates destructive conflict.](https://scaleops.com/blog/the-complete-guide-to-kubernetes-management-in-2025-7-pillars-for-production-scale/) VPA wants to restart pods to apply new resource requests. HPA wants to maintain a stable replica count. Their behaviors fight each other.

## Deployment Strategies: Tradeoffs

Two strategies dominate production:

**Blue-Green Deployment**: Maintain two complete production environments. Route all traffic to blue (current). Deploy to green (new). Once green is validated, switch all traffic at once.
- Advantage: Fast switchover, instant rollback (just switch back)
- Disadvantage: Expensive (need two full production environments), complex to keep in sync

**Canary Deployment**: Route a small percentage of traffic (2%, 25%, 75%) to new version. Monitor metrics. Gradually increase percentage or rollback if metrics degrade.
- Advantage: Cheap (no duplicate environment), risk is proportional to percentage, real-world testing
- Disadvantage: Requires careful monitoring, more complex to implement, slower rollout

[Choice depends on resources and risk tolerance.](https://octopus.com/devops/software-deployments/blue-green-vs-canary-deployments/) Cost-constrained teams use canary. Teams with resources and low risk tolerance use blue-green.

Most production systems blend both: canary rollout (1% → 10% → 50% → 100%) with automated rollback, plus a blue-green standby for manual emergency rollback.

## CI/CD Principles

[GitHub Actions (or any CI/CD) should enforce these principles:](https://github.blog/enterprise-software/ci-cd/build-ci-cd-pipeline-github-actions-four-steps/)

**Code quality gates before deployment**: Run tests, linting, security scanning. Block deployment if tests fail. This is automatic, fast feedback.

**Secrets are never in logs**: Credentials, API keys, tokens should never appear in logs or output. Use secret management (GitHub Secrets, HashiCorp Vault) and inject at runtime.

**Immutable artifacts**: Once you build an image, it should never change. Tag with commit SHA, not "latest". If you redeploy the same SHA, you get identical behavior.

**Clear separation between environments**: Dev/staging/production should be separate. Different secrets, different quotas, different monitoring. A broken test should not affect production.

**Visible feedback**: Build and deployment results should be visible to the team. Did the deploy succeed or fail? Is it in progress? What version is running in production right now?

## Container Registry and Supply Chain

[Container registries are critical infrastructure because they are the source of truth for what code is running.](https://www.wiz.io/academy/container-security/container-registries/) A compromised registry means compromised deployments.

Key risks:
- **Write access**: If an attacker can push images, they can inject malicious code into your system
- **Image verification**: How do you know the image you're pulling is actually from you and not tampered with?
- **Version retention**: If you delete old image versions, rollback becomes impossible
- **Scanning**: Before deploying an image, scan it for known vulnerabilities

[Supply chain attacks happen here.](https://www.trendmicro.com/vinfo/us/security/news/virtualization-and-cloud/exposed-container-registries-a-potential-vector-for-supply-chain-attacks/) An attacker gains write access to a registry. Pushes a compromised image. Your CI/CD system pulls it and deploys it. Now your production system is running malicious code.

Prevention: private registries, image signing, vulnerability scanning, access control, audit logs.

## Deployment Failures and Rollback

[Deployment can fail in predictable ways:](https://oneuptime.com/blog/post/2026-01-24-rollback-deployment-issues/view) image doesn't exist in registry, configuration is wrong, database schema incompatible, insufficient resources, health checks fail.

Rollback is harder than deployment:
- Previous image might be deleted from registry
- Database schema changes may be incompatible with old code
- Cached data may assume new version's format

[A frozen deployment is worse than a broken one](https://learnkube.com/kubernetes-rollbacks): system is stuck in neither direction.

Prevent by: testing rollback before deploying, retaining old images, using reversible migrations, monitoring rollout progress.

## References and Further Reading

[Kubernetes In Production: 7 Key Challenges](https://octopus.com/devops/kubernetes-deployments/kubernetes-in-production/)
- Overview of the gap between "pods running" and "system working"

[Configure Liveness, Readiness and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- Official Kubernetes documentation on health checks and probe configuration

[kubectl rollout Best Practices for Production (2025 Guide)](https://scaleops.com/blog/kubectl-rollout-7-best-practices-for-production-2025/)
- Specific guidance on deployment and rollback operations

[Blue-Green and Canary Deployments Explained](https://www.harness.io/blog/blue-green-canary-deployment-strategies)
- Comparison of deployment strategies with tradeoff analysis

[How to Build a CI/CD Pipeline with GitHub Actions in Four Simple Steps](https://github.blog/enterprise-software/ci-cd/build-ci-cd-pipeline-github-actions-four-steps/)
- Practical CI/CD workflow design

[Container Registry Security: Best Practices](https://dev.to/kapusto/securing-container-registries-best-practices-for-safe-image-management-3lj0)
- Image registry security and supply chain protection

[Kubernetes Best Practices for Production](https://kubernetes.io/docs/concepts/configuration/overview/)
- Official guidance on resource management and configuration

---

## Applying This to Your Deployment

Deploy a pre-trained model API to GKE with working CI/CD. Think operationally:

1. **Can you detect failures?** (readiness/liveness probes)
2. **What happens when failure occurs?** (graceful degradation or hard fail?)
3. **How do you verify deployment succeeded?** (health checks, not just "pod running")
4. **How do you rollback?** (image retention, tested procedure)
5. **Can you trust the pipeline?** (security, immutable artifacts, visible progress)
6. **What are your constraints?** (startup latency, replica cost, image storage)

These are operational questions. The scripts come second.
