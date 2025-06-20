# 🧠 Knowledge Transfer FAQ – New Joiner & Senior Engineer Chat

---

**New Joiner:**  
Hi! During KT, I heard a lot about “client-specific extensions.” Can you explain what that means?

**Senior Engineer:**  
Client-specific extensions refer to custom features or modules we build for a particular client’s needs, beyond our base platform. These are usually maintained in a separate repository or namespace to avoid conflicts with the core product updates.

---

**New Joiner:**  
How do I know which part of the codebase is safe to modify and which is off-limits?

**Senior Engineer:**  
You should only make changes in the `commerceiq-client-extensions` or `custom-hooks` folders unless explicitly told otherwise. Avoid modifying the `core` and `shared-services` folders without team approval.

---

**New Joiner:**  
What’s the difference between “prod push” and “client UAT deployment”?

**Senior Engineer:**  
“Prod push” is deployment to the live environment. “Client UAT” is a staging environment for client validation before going live. It’s our final QA checkpoint.

---

**New Joiner:**  
Who decides what features we build for the client?

**Senior Engineer:**  
Our Business Analyst works with the client’s Product Owner and our Solution Architect to finalize requirements. We then scope and prioritize them in sprints.

---

**New Joiner:**  
I noticed some services are in Python and some in Node.js. Is there a reason?

**Senior Engineer:**  
Yes. Python is used for data-heavy tasks like ML pipelines. Node.js is used for real-time APIs and services due to its event-driven nature.

---

**New Joiner:**  
What’s the standard process for raising a production issue?

**Senior Engineer:**  
Raise a Jira ticket, tag it as “P1 - Production”, and ping `#incident-response` on Slack. Check logs via Datadog before escalation.

---

**New Joiner:**  
In KT, someone mentioned “SLA breach alerts.” How are those monitored?

**Senior Engineer:**  
We monitor SLAs using Datadog and New Relic. If an API breaches its response time SLA, alerts are automatically triggered.

---

**New Joiner:**  
Who handles versioning and API documentation?

**Senior Engineer:**  
The platform team does. We use Swagger for docs and follow semantic versioning: `MAJOR.MINOR.PATCH` (e.g., `2.3.1`).

---

**New Joiner:**  
How do I access client-specific credentials or tokens for testing?

**Senior Engineer:**  
They’re stored in Vault. Request access through your project lead. Never commit credentials to code or version control.

---

**New Joiner:**  
Can I reach out to the client directly if I have a question?

**Senior Engineer:**  
Not directly. Go through the BA or Scrum Master to ensure consistent communication and context.

---

**New Joiner:**  
How do I know if a bug I found is already reported?

**Senior Engineer:**  
Search Jira with keywords. If it’s new, create a ticket and link logs/screenshots. Use the “Bug” type and assign it to the module owner.

---

**New Joiner:**  
What are "shared libraries" and when should I use them?

**Senior Engineer:**  
They’re reusable code packages (e.g., logging, auth). Always check if one exists before writing new logic.

---

**New Joiner:**  
I heard we use CI/CD—can you walk me through our deployment pipeline?

**Senior Engineer:**  
Sure. We use GitHub Actions for CI and Argo CD for CD. On every pull request, unit tests and linters run automatically. Once approved and merged to `main`, Argo CD syncs the deployment to the staging environment. Production pushes require a manual approval step.

---

**New Joiner:**  
What’s the difference between staging, QA, and sandbox environments?

**Senior Engineer:**  
Good question. Sandbox is for developers to test freely. QA is where our testers validate features. Staging mirrors production and is used for final verification before a live deployment.

---

**New Joiner:**  
Which cloud platform are we using and why?

**Senior Engineer:**  
We use AWS because most of our clients already have AWS contracts. It also integrates well with our Kubernetes setup, managed via EKS (Elastic Kubernetes Service).

---

**New Joiner:**  
What are some key business KPIs we should be aware of?

**Senior Engineer:**  
Client satisfaction (CSAT), SLA adherence, monthly active users (MAUs), feature adoption rate, and defect leakage rate are key KPIs we track. These drive decision-making during reviews and retrospectives.

---

**New Joiner:**  
How do sprint planning and estimations work in our team?

**Senior Engineer:**  
We follow 2-week sprints. During sprint planning, each ticket is sized using story points. We use Fibonacci estimates (1, 2, 3, 5, 8, 13) based on effort and complexity. BAs and developers collaborate to clarify scope before estimation.

---

**New Joiner:**  
What architecture pattern do we follow?

**Senior Engineer:**  
Most projects follow a microservices architecture. Each service owns a specific domain (e.g., billing, auth) and communicates via REST or gRPC. We use an API gateway for routing and service mesh for observability and security.

---

**New Joiner:**  
How do we handle secrets and environment variables?

**Senior Engineer:**  
All secrets are managed via AWS Secrets Manager and injected at runtime. Never hardcode or commit any secret. We use `.env.example` files to indicate expected keys locally.

---

**New Joiner:**  
Where can I see system-level diagrams or architecture overviews?

**Senior Engineer:**  
They’re stored in our internal Confluence under the “Engineering → Architecture Diagrams” section. You can also request walkthroughs during onboarding or team syncs.

---

**New Joiner:**  
What’s the process if I want to propose a new tool or framework?

**Senior Engineer:**  
Create a design doc outlining the problem, proposed solution, alternatives considered, risks, and migration plan. Share it in the `#eng-architecture` channel for feedback and final approval from the architecture committee.

---

**New Joiner:**  
If a service is slow, how do I troubleshoot it?

**Senior Engineer:**  
Start with distributed tracing via Datadog APM. Check metrics like response time, error rate, and throughput. Look into logs, and if needed, simulate the traffic using Postman or load test tools like k6.

---


**New Joiner:**  
Who approves my access to internal tools like Jira, GitHub, and Confluence?

**Senior Engineer:**  
Access is granted by the project’s onboarding coordinator or tech lead. Raise a request through the IT portal and tag your project lead for approval. Most accounts are provisioned within 24–48 hours.

---

**New Joiner:**  
Is there a checklist I should follow to complete my onboarding?

**Senior Engineer:**  
Yes. You’ll find the onboarding checklist in the "Welcome Kit" shared on Day 1. It includes tasks like setting up dev environments, reading through architecture docs, and shadowing KT sessions. Ask your buddy or onboarding manager for any gaps.

---

**New Joiner:**  
How soon can I start picking up development tasks?

**Senior Engineer:**  
You can usually start shadowing tasks in the second week. You’ll begin with low-risk issues like UI bugs or unit test coverage. Once your KT and onboarding checklist are complete, the team lead will assign sprint tickets.

---

**New Joiner:**  
How are features prioritized in our roadmap?

**Senior Engineer:**  
Our product roadmap is shaped by business goals, client feedback, and technical debt. Product Managers gather input from stakeholders and engineering leads to define quarterly OKRs. Priority is driven by value-to-effort ratio and delivery deadlines.

---

**New Joiner:**  
How often does the product roadmap change?

**Senior Engineer:**  
It’s reviewed every quarter. However, mid-sprint changes may happen if a client has urgent needs or business goals shift. We try to buffer 20% sprint capacity for unplanned items.

---

**New Joiner:**  
If I have a product improvement idea, how can I share it?

**Senior Engineer:**  
Document your idea in a Confluence page or design doc and bring it up in the next sprint retro or roadmap planning. We encourage bottom-up innovation—some of our best features came from developers!

---

**New Joiner:**  
Can I attend client calls?

**Senior Engineer:**  
Absolutely, especially if you’re working directly on their requirements. Just loop in the BA or Project Manager and be prepared with notes. It’s a great way to understand their expectations and context.

---

**New Joiner:**  
What should I never do when communicating with clients?

**Senior Engineer:**  
Never make promises on delivery timelines or technical feasibility unless cleared by your team lead or PM. Avoid using internal jargon or sharing internal blockers without framing a solution.

---

**New Joiner:**  
How do we document client-specific requirements?

**Senior Engineer:**  
We track them in Jira with a “Client Request” tag and detailed acceptance criteria. The related context is captured in Confluence with mockups, use-case flows, and approval status from client meetings.

---

**New Joiner:**  
What happens if the client changes scope mid-sprint?

**Senior Engineer:**  
The BA negotiates the impact with the client and updates the Jira backlog. We try to de-scope equivalent tasks or move them to the next sprint. Always notify the Scrum Master if your ticket priority changes.

---

**New Joiner:**  
If something breaks in production after hours, what should I do?

**Senior Engineer:**  
Check the on-call rotation calendar (available on Confluence). Ping the on-call engineer in `#incident-response`, and open a high-priority Jira ticket. If it’s client-facing, notify your project manager immediately.

---

**New Joiner:**  
What qualifies as a P0 vs P1 vs P2 issue?

**Senior Engineer:**  
- **P0** – Critical outage (e.g., app down, data loss)  
- **P1** – Major feature broken or SLA breached  
- **P2** – Non-blocking bugs or performance degradation  
We triage daily, but P0 issues are addressed immediately.

---

**New Joiner:**  
How are postmortems handled?

**Senior Engineer:**  
We conduct a postmortem within 48 hours of a major incident. It includes root cause analysis, contributing factors, resolution steps, and action items to prevent recurrence. Templates are in Confluence under "Incident Reviews."

---

**New Joiner:**  
What’s the standard for writing internal documentation?

**Senior Engineer:**  
Follow our documentation guidelines in the Engineering Handbook. Use the `docs/` folder for repo-specific notes. For broader guides, use Confluence. Every doc should include: objective, stakeholders, last updated date, and links to relevant Jira tickets.

---

**New Joiner:**  
How do we keep documentation up to date?

**Senior Engineer:**  
We update docs as part of our Definition of Done (DoD) for each ticket. Also, we hold quarterly “Doc Days” where teams audit and clean up outdated documentation.

---

**New Joiner:**  
Is there a naming convention for repositories and branches?

**Senior Engineer:**  
Yes. Repos follow the format: `client-project-module`. Branches use `feature/`, `bugfix/`, or `hotfix/` prefixes. For example: `feature/user-auth-logging`. Refer to our GitFlow policy in the developer wiki.

---

**New Joiner:**  
What’s the PM’s role in our daily work?

**Senior Engineer:**  
The PM ensures delivery aligns with client goals. They handle roadmap prioritization, stakeholder alignment, and define success metrics. You’ll mostly work with them during sprint planning and demos.

---

**New Joiner:**  
How closely do we work with QA?

**Senior Engineer:**  
Very closely. QA writes test cases during development and helps define acceptance criteria. For each feature, developers write unit tests, and QA covers integration and end-to-end cases. Sync with QA during grooming and prior to staging releases.

---

**New Joiner:**  
What’s DevOps responsible for here?

**Senior Engineer:**  
DevOps owns infrastructure provisioning, CI/CD pipelines, monitoring, and alerting. They also help with release coordination and rollback plans. Don’t hesitate to involve them early when deploying new services or DB migrations.

---

**New Joiner:**  
If I want to experiment with a new architecture pattern, who should I involve?

**Senior Engineer:**  
Start with your tech lead and create a lightweight proposal. If the scope is large or affects other teams, bring it to the Architecture Review Board (ARB). They meet biweekly and review all major technical decisions.

---

**New Joiner:**  
What should I check first if a service is running slow?

**Senior Engineer:**  
Start by checking logs and APM dashboards like Datadog or New Relic. Look for high response times, DB query delays, or memory spikes. Also, check whether recent deployments introduced regressions.

---

**New Joiner:**  
How do we monitor database performance?

**Senior Engineer:**  
We use AWS CloudWatch and Datadog to track slow queries, CPU usage, and connection pools. Use `EXPLAIN` plans in PostgreSQL to analyze inefficient queries and look for missing indexes.

---

**New Joiner:**  
Are there any performance SLAs I should be aware of?

**Senior Engineer:**  
Yes, most APIs have target response times (e.g., under 500ms). These SLAs are tracked in Datadog, and breaches trigger alerts. Refer to the API contract or client agreement for specifics.

---

**New Joiner:**  
What are our guidelines for writing performant code?

**Senior Engineer:**  
Favor async operations, reduce redundant API calls, batch DB writes/reads, and avoid unnecessary object creation in loops. Use pagination for large data sets and cache frequently accessed data using Redis.

---

**New Joiner:**  
What’s expected of me during a code review?

**Senior Engineer:**  
Check for:  
- Functionality correctness  
- Code readability and maintainability  
- Test coverage  
- Adherence to our coding standards  
Leave constructive feedback and approve only when all criteria are met.

---

**New Joiner:**  
How long should a code review take?

**Senior Engineer:**  
Aim to complete reviews within 24 hours. If a PR is urgent, the author should notify reviewers in Slack. Large PRs should ideally be split into smaller parts for faster turnaround.

---

**New Joiner:**  
What kind of comments are encouraged in code reviews?

**Senior Engineer:**  
Use a positive, collaborative tone. Focus on why something might need improvement, suggest alternatives, and highlight good practices. Avoid vague comments—be specific and helpful.

---

**New Joiner:**  
Do we have automated checks during code review?

**Senior Engineer:**  
Yes. Our CI pipeline runs linting, unit tests, and security checks on every PR. Reviews won’t pass unless all checks are green. For new dependencies, ensure they are security-vetted.

---

**New Joiner:**  
What are our responsibilities around data privacy?

**Senior Engineer:**  
We follow GDPR and SOC 2 standards. Avoid logging PII, encrypt sensitive data in transit and at rest, and restrict access via IAM roles. Always use approved libraries for encryption and hashing.

---

**New Joiner:**  
How do I know if a field contains personally identifiable information (PII)?

**Senior Engineer:**  
If it can be used to directly or indirectly identify someone (e.g., name, email, IP address, health info), it's PII. Always mask, encrypt, or anonymize such fields when logging or storing.

**New Joiner:**  
Do we need user consent to track application behavior?

**Senior Engineer:**  
Yes. We include consent management in our applications. Tracking scripts and analytics tools are only triggered after the user agrees. For mobile apps, permissions are handled via native SDKs.

---

**New Joiner:**  
Where can I find our security and compliance guidelines?

**Senior Engineer:**  
They’re in Confluence under “Security & Compliance.” It includes protocols for handling incidents, password policies, data retention, third-party tools, and vendor risk assessments.

---

**New Joiner:**  
Where do we store our raw and processed data?

**Senior Engineer:**  
Raw data is stored in Amazon S3 buckets, and processed datasets go into Redshift or Snowflake depending on the client. We use folder prefixes like `/raw`, `/cleaned`, and `/aggregated` to organize them.

---

**New Joiner:**  
What tools are used to build data pipelines here?

**Senior Engineer:**  
We primarily use Apache Airflow for orchestration, with Python or SQL-based tasks. Some legacy pipelines use AWS Glue. We also leverage dbt for data transformations in the warehouse.

---

**New Joiner:**  
How do I monitor if a pipeline has failed?

**Senior Engineer:**  
Airflow has a web UI where failed tasks are marked red. You’ll also receive Slack alerts if you’re listed as a DAG owner. Check the logs linked from the UI to debug failures.

---

**New Joiner:**  
What’s the process for deploying a new ML model?

**Senior Engineer:**  
First, package the model using MLflow or ONNX. Then, containerize it with Docker. It’s deployed via our Kubernetes cluster using Helm charts. Each model runs as a microservice behind an API gateway.

---

**New Joiner:**  
Where should I log model predictions?

**Senior Engineer:**  
Log them to a dedicated table in our analytics DB with fields like `timestamp`, `input_hash`, `prediction`, and `model_version`. Be mindful of privacy—don’t log PII with inputs.

---

**New Joiner:**  
How do we track model performance in production?

**Senior Engineer:**  
We monitor metrics like prediction latency, accuracy drift, and model input anomalies. These are tracked using Prometheus + Grafana dashboards. Retraining is triggered when drift exceeds thresholds.

---

**New Joiner:**  
What’s the handoff process between backend and frontend teams?

**Senior Engineer:**  
Backends expose versioned APIs documented via Swagger. Frontend developers sync with backend leads during sprint planning and review contracts together. We use Postman collections for testing endpoints before integration.

---

**New Joiner:**  
How do we handle API versioning for frontend consumption?

**Senior Engineer:**  
Every breaking change results in a new version (e.g., `/v2/orders`). Backward-compatible changes are added to existing endpoints with clear documentation. Deprecation timelines are shared well in advance.

---

**New Joiner:**  
What’s our design-to-implementation process for frontend features?

**Senior Engineer:**  
Designs come from Figma, reviewed jointly by frontend devs and UX designers. After sign-off, frontend devs sync with backend on API requirements and use mock APIs until endpoints are ready.

---

**New Joiner:**  
Where do we track integration bugs between frontend and backend?

**Senior Engineer:**  
Integration issues are tracked in Jira under the “FE-BE Sync” epic. We also hold weekly frontend-backend syncs to surface blockers early and avoid misalignment.

---
---

# Rich Internal Conversations Knowledge Base

Conversations are grouped by relevant Slack channels. Each block represents a complete Q&A exchange between an employee (Anonymous) and an internal expert. Use them for retrieval‑augmented generation.

---

#finance-help
Anonymous: What’s the formula we use to calculate Net Dollar Retention?
Leila-FP&A: Net Dollar Retention = (Recurring Revenue from current customers this quarter ÷ Recurring Revenue from the same cohort last year) × 100. We exclude churned customers by ID and include upsells tagged “UP”.

---

#finance-help
Anonymous: Where can I find the monthly burn multiple dashboard?
Leila-FP&A: It’s in Looker → Finance / Burn Analysis / “Burn Multiple – Board View”. Source sheet is gs://fin-metrics/burn_multiple_raw.parquet.

---

#product-analytics
Anonymous: Which table stores daily active users segmented by feature flag?
Sasha-Data: Use analytics.dau_by_featureflag_daily. It joins to dim_feature_flag on flag_id.

---

#product-ops
Anonymous: How do I enable the “dark_mode_beta” flag for customer ABC?
Vik-ProdOps: Go to LaunchDarkly → Projects / WebApp / Flags / dark_mode_beta. Under “Targeting”, add account_id = 38177. Save and wait ~2 min for cache propagation.

---

#dev-support
Anonymous: Yarn install fails with “ETIMEDOUT registry.corp.local”.
Arjun-Platform: Set npm config registry to https://registry.corp.local and export HTTP_PROXY=http://proxy.internal:3128. Then rerun yarn install.

---

#dev-support
Anonymous: Where’s the Helm chart for the griffin-worker microservice?
Arjun-Platform: charts/griffin/ in the ops-helm repo. Version is pinned at 1.7.2 in deploy/griffin/values-prod.yaml.

---

#sre-alerts
Anonymous: Grafana is alerting “High queue depth” for merlin-db. Next step?
Dana-SRE: Connect to merlin-db-primary and run `show full processlist;` to spot long‑running queries. If queue depth > 500 for >5 min, fail over using `clusterctl switchover merlin`.

---

#observability
Anonymous: Loki log query for service payments-api timing out, any optimizations?
Dana-SRE: Add `| json | line_format "{{.request_id}} {{.duration_ms}}"` and set `limit=5000`. Also use `payment_service` label rather than wildcard.

---

#legal
Anonymous: Who approves trademark usage in conference talks?
Aisha-Legal: Send deck to legal-trademarks@company.net at least 5 business days before the event. I’ll review and return a signed approval PDF.

---

#marketing
Anonymous: What’s the internal code name for the upcoming billing revamp?
Eddie-Marketing: “Project Zephyr”. Public name TBD; keep internal until launch date in October.

---

#marketing
Anonymous: Our homepage claims “Servers launch in <1 s”. Where’s the benchmark data?
Eddie-Marketing: Results in Confluence page “Launch Speed Benchmarks 2025‑03”. Raw measurements in s3://benchmarks/launch_local_cluster_2025_03.csv.

---

#design-system
Anonymous: Where is the latest Figma library for UI components?
Lara-Design: Figma → Team “Design‑System” → File “DS‑Library 2.1”. Components are published; run “Update library” in your file.

---

#hr-people
Anonymous: How do I record overseas work days for tax reporting?
Maya-HR: In Workday, choose “International Remote Work” as time type, then specify country and dates. HR auto‑generates a tax packet after 30 days cumulative.

---

#hr-people
Anonymous: Emergency PTO request protocol?
Maya-HR: DM your manager and CC hr-people@company.net. HR will retroactively approve PTO in Workday.

---

#security
Anonymous: How do I request a temporary AWS IAM role with S3 write access?
Noah-SecOps: Open AccessHub → “New Privileged Role”. Select role template `s3_write_temp`. Maximum duration 4 h, requires manager approval.

---

#security
Anonymous: What’s the process for reporting a potential phishing email?
Noah-SecOps: Forward the email as attachment to phish@company.net. Security will analyze and update the threat feed.

---

#data-governance
Anonymous: Retention period for event logs in eventstore.raw_events?
Ola-DataGov: Raw events are retained 180 days. Aggregated events in analytics.* are retained 3 years.

---

#data-governance
Anonymous: How do I request a new GDPR data‑subject export?
Ola-DataGov: Submit a JIRA ticket in project “DPR” with customer_id. Exports run nightly at 02:00 UTC and drop ZIP files in s3://gdpr-exports/<ticket-id>/

---

#dev-environment
Anonymous: First‑time setup for monorepo on Apple M4 chips?
Zara-DevXP: Use setup‑m4.sh in repo root. It installs Homebrew, Volta, and Rosetta, then runs `npm run bootstrap`.

---

#dev-environment
Anonymous: What’s the VPN config profile name for development cluster?
Zara-DevXP: “Corp‑Dev‑VPN‑v2”. Download from Okta → “VPN Profiles”.

---

#sales-ops
Anonymous: SQL to pull renewal pipeline for Q3?
Tom-SalesOps: ```sql
SELECT opp_id, account_name, arr, stage
FROM crm.snapshot_renewals
WHERE close_quarter = '2025Q3'
  AND stage IN ('Commit', 'Best Case');
```

---

#cust-success
Anonymous: Where do we track Net Promoter Score responses?
Ivy-CS: Table cs.nps_responses. Dashboard in Mode → “Customer Health / NPS Trend”.

---

#support
Anonymous: How do I restart the recommendation-engine without downtime?
Jules-Support: Use `deployctl rollout recommender --strategy=canary --steps=2`. Canary lasts 15 min before full rollout.

---

#support
Anonymous: Location of client-side error logs for the iOS app?
Jules-Support: Logs are posted to Crashlytics; raw JSON export is in BigQuery dataset mobile_crashlytics. Use table ios_crashes_daily.

---

#mobile-dev
Anonymous: How do I bump the iOS version code automatically during CI?
Elena-Mobile: Set `AUTO_INCREMENT_BUILD_NUMBER=true` in CircleCI env vars. fastlane’s `increment_build_number` picks it up.

---

#mobile-dev
Anonymous: TestFlight invite quota exceeded. Can we reset?
Elena-Mobile: Remove stale tester groups in App Store Connect → TestFlight → Groups. Each deletion frees slots instantly.

---

#ai-research
Anonymous: Where are the latest fine‑tuned Llama-2 checkpoints?
Rahul-ML: Check s3://ml-models/llama2-finetune/2025‑06‑02/. Each folder has config.json and adapter weights.

---

#ai-research
Anonymous: How do I request a new GPU pod in the research cluster?
Rahul-ML: Submit run spec in Pachyderm UI. Choose pool “gpu-a100” and set time limit. Default quota is 24 h; extensions via #ml-platform.

---

#legal
Anonymous: NDA template for academic partners?
Aisha-Legal: Legal drive → Templates → “Mutual NDA Academic v4.docx”.

---


