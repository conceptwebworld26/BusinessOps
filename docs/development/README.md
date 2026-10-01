# Development History

Date-wise record of how BusinessIQ was built. One record per meaningful implementation
milestone, named `YYYY-MM-DD-<slug>.md`.

**Append-only.** A record is never edited to reflect later understanding and never
overwritten. To correct one, write a new record with a `Supersedes:` line and leave the
original intact. Reading these in date order should let someone unfamiliar with the project
understand how it evolved and why.

Template: [`../templates/dev-record.md`](../templates/dev-record.md).

| Date | Milestone | Record |
|---|---|---|
| 2026-09-08 | 0 — Architecture Gate | [architecture gate](2026-09-08-milestone-0-architecture-gate.md) |
| 2026-09-08 | 0 — Review Corrections (Rev 2) | [architecture review corrections](2026-09-08-architecture-review-corrections.md) |
| 2026-09-08 | 1 — Foundation | [foundation](2026-09-08-foundation.md) |
| 2026-09-08 | 2 — Vertical Slice | [vertical slice](2026-09-08-vertical-slice.md) |
| 2026-09-08 | 3 — Data Layer | [data layer](2026-09-08-data-layer.md) |
| 2026-09-08 | 4 — Data Quality | [data quality](2026-09-08-data-quality.md) |
| 2026-09-08 | 5 — KPI Engine | [kpi engine](2026-09-08-kpi-engine.md) |
| 2026-09-08 | 6 — Internal Analytics Skills | [internal analytics](2026-09-08-internal-analytics.md) |
| 2026-09-09 | 7 — Internal Analytics Commands | [internal analytics commands](2026-09-09-internal-analytics-commands.md) |
| 2026-09-09 | 8 — Forecasting & Anomaly Detection | [forecasting and anomaly detection](2026-09-09-forecasting-anomaly.md) |
| 2026-09-10 | 8 — Closure · 9 — Gate preparation | [M8 closure and M9 gate preparation](2026-09-10-m8-closure-m9-gate-preparation.md) |
| 2026-09-10 | 9 — Architecture & scope review | [M9 architecture review](2026-09-10-m9-architecture-review.md) |
| 2026-09-10 | 9 — Owner decisions & governance lock | [M9 owner decisions](2026-09-10-m9-owner-decisions.md) |
| 2026-09-10 | 9-A — Research core & disclosure gate | [M9-A research core](2026-09-10-m9a-research-core-disclosure-gate.md) |
| 2026-09-10 | 9-B — Research scout & controlled retrieval | [M9-B scout retrieval](2026-09-10-m9b-research-scout-retrieval.md) |
| 2026-09-10 | M9-B: live verification and closure | [m9b live verification closure](2026-09-10-m9b-live-verification-closure.md) |
| 2026-09-10 | M9-B: is there a real scout transport? (supersedes the M9-B completion claim) | [m9b scout transport investigation](2026-09-10-m9b-scout-transport-investigation.md) |
| 2026-09-10 | M9-B: the retrieval vertical slice, and the defect that hid inside it | [m9b vertical slice](2026-09-10-m9b-vertical-slice.md) |
| 2026-09-11 | M9-C.1: scout return-contract hardening | [m9c1 scout return contract hardening](2026-09-11-m9c1-scout-return-contract-hardening.md) |
| 2026-09-11 | M9-C.10: controlled scout handoff trial | [m9c10 controlled scout handoff trial](2026-09-11-m9c10-controlled-scout-handoff-trial.md) |
| 2026-09-11 | M9-C.11: fresh-session agent registration verification | [m9c11 fresh session agent registration](2026-09-11-m9c11-fresh-session-agent-registration.md) |
| 2026-09-11 | M9-C.2: advisory-language guard, documentation correction | [m9c2 advisory guard wording](2026-09-11-m9c2-advisory-guard-wording.md) |
| 2026-09-11 | M9-C.3: `biq-company-analysis` skill | [m9c3 company analysis skill](2026-09-11-m9c3-company-analysis-skill.md) |
| 2026-09-11 | M9-C.4: structured evidence conflict transport | [m9c4 conflict transport](2026-09-11-m9c4-conflict-transport.md) |
| 2026-09-11 | M9-C.6: live classifier verification and policy-question record | [m9c6 live classifier verification](2026-09-11-m9c6-live-classifier-verification.md) |
| 2026-09-11 | M9-C.6: source-tier classifier hardening | [m9c6 tier classifier hardening](2026-09-11-m9c6-tier-classifier-hardening.md) |
| 2026-09-11 | M9-C.7: scout return-contract enforcement — investigation and outcome | [m9c7 scout return contract enforcement](2026-09-11-m9c7-scout-return-contract-enforcement.md) |
| 2026-09-11 | M9-C.8: research handoff operationalization — investigation and outcome | [m9c8 research handoff operationalization](2026-09-11-m9c8-research-handoff-operationalization.md) |
| 2026-09-11 | M9-C.9: scout output shape experiment | [m9c9 scout output shape experiment](2026-09-11-m9c9-scout-output-shape-experiment.md) |
| 2026-09-12 | M9-C.12: plugin installation and agent source resolution audit | [m9c12 plugin agent source resolution audit](2026-09-12-m9c12-plugin-agent-source-resolution-audit.md) |
| 2026-09-12 | M9-C.13: fresh-session live trial of the `BIQ-REC/1` handoff protocol | [m9c13 fresh session biq rec trial](2026-09-12-m9c13-fresh-session-biq-rec-trial.md) |
| 2026-09-13 | M9-C.14: zero-record representation and full `close_retrieval()` integration | [m9c14 zero record close retrieval](2026-09-13-m9c14-zero-record-close-retrieval.md) |
| 2026-09-13 | M9-C.15: formal `BIQ-REC/1` / `BIQ-END/1` production adoption | [m9c15 biq rec production adoption](2026-09-13-m9c15-biq-rec-production-adoption.md) |
| 2026-09-13 | M9-C.16: live production smoke test and Company Analysis end-to-end demonstration | [m9c16 live production smoke company analysis](2026-09-13-m9c16-live-production-smoke-company-analysis.md) |
| 2026-09-13 | M9-C.17: first-party source registry and superseded-contract cleanup | [m9c17 first party registry and protocol cleanup](2026-09-13-m9c17-first-party-registry-and-protocol-cleanup.md) |
| 2026-09-13 | M9-D.1: the `/company-analysis` command | [m9d1 company analysis command](2026-09-13-m9d1-company-analysis-command.md) |
| 2026-09-13 | M9-D.2: Market Analysis skill and `/market-analysis` command | [m9d2 market analysis](2026-09-13-m9d2-market-analysis.md) |
| 2026-09-14 | M10.1 Cross-Domain Synthesis Foundation | [m10 1 synthesis foundation](2026-09-14-m10-1-synthesis-foundation.md) |
| 2026-09-14 | M9-D.3: Competitor Analysis Skill + `/competitor-analysis` command | [m9d3 competitor analysis](2026-09-14-m9d3-competitor-analysis.md) |
| 2026-09-14 | M9-D.4 Research Intent Architecture Consolidation | [m9d4 research intent registry](2026-09-14-m9d4-research-intent-registry.md) |
| 2026-09-14 | M9-D.5 Industry Research Skill and `/industry-research` command | [m9d5 industry research](2026-09-14-m9d5-industry-research.md) |
| 2026-09-15 | M10.2-R live: the compatibility ALLOW branch, on real evidence | [m10 2r live allow branch verification](2026-09-15-m10-2r-live-allow-branch-verification.md) |
| 2026-09-15 | M10.2-R: internal provenance footing, and the retrieval → synthesis seam | [m10 2r provenance footing and seam](2026-09-15-m10-2r-provenance-footing-and-seam.md) |
| 2026-09-15 | M10.2-R.1: cross-domain unit semantics, decided not implemented | [m10 2r1 cross domain unit semantics](2026-09-15-m10-2r1-cross-domain-unit-semantics.md) |
| 2026-09-15 | M10.2-R.10: the Company Analysis command reaches the strict footing path | [m10 2r10 company analysis command footing](2026-09-15-m10-2r10-company-analysis-command-footing.md) |
| 2026-09-15 | M10.2-R.2: canonical unit semantics, implemented | [m10 2r2 canonical unit semantics](2026-09-15-m10-2r2-canonical-unit-semantics.md) |
| 2026-09-15 | M10.2-R.3: the internal↔external ALLOW branch, on a deterministic fixture | [m10 2r3 deterministic allow branch](2026-09-15-m10-2r3-deterministic-allow-branch.md) |
| 2026-09-15 | M10.2-R.6: dimension provenance and source-context admissibility | [m10 2r6 dimension provenance](2026-09-15-m10-2r6-dimension-provenance.md) |
| 2026-09-15 | M10.2-R.8: source-context capture and currency-code admissibility | [m10 2r8 source context capture](2026-09-15-m10-2r8-source-context-capture.md) |
| 2026-09-15 | M10.2-R.9: Company Analysis authors dimension footings | [m10 2r9 company analysis footings](2026-09-15-m10-2r9-company-analysis-footings.md) |
| 2026-09-16 | M10.2-R.11: Market Analysis reaches the strict footing path | [m10 2r11 market analysis footing](2026-09-16-m10-2r11-market-analysis-footing.md) |
| 2026-09-16 | M10.2-R.12: Competitor Analysis reaches the strict footing path | [m10 2r12 competitor analysis footing](2026-09-16-m10-2r12-competitor-analysis-footing.md) |
| 2026-09-16 | M10.2-R.13: Industry Research reaches the strict footing path | [m10 2r13 industry research footing](2026-09-16-m10-2r13-industry-research-footing.md) |
| 2026-09-16 | M10.2-R.14: the local join, internal analysis reaches strict synthesis | [m10 2r14 local join](2026-09-16-m10-2r14-local-join.md) |
| 2026-09-16 | M10.3.1: SWOT, the first consumer of the synthesis representation | [m10 3 1 swot](2026-09-16-m10-3-1-swot.md) |
| 2026-09-16 | M10.3.2-A: Strategy recommendation contract (decision only) | [m10 3 2 a strategy recommendation contract](2026-09-16-m10-3-2-a-strategy-recommendation-contract.md) |
| 2026-09-16 | M10.3.2: Strategy Recommendations | [m10 3 2 strategy recommendations](2026-09-16-m10-3-2-strategy-recommendations.md) |
| 2026-09-16 | M10.3.3-A: Decision Support contract (decision only) | [m10 3 3 a decision support contract](2026-09-16-m10-3-3-a-decision-support-contract.md) |
| 2026-09-16 | M10.3.3: Decision Support contract-alignment remediation | [m10 3 3 contract alignment remediation](2026-09-16-m10-3-3-contract-alignment-remediation.md) |
| 2026-09-16 | M10.3.3: Decision Support | [m10 3 3 decision support](2026-09-16-m10-3-3-decision-support.md) |
| 2026-09-16 | M10.3.4: Executive Report contract (decision only) | [m10 3 4 executive report contract](2026-09-16-m10-3-4-executive-report-contract.md) |
| 2026-09-17 | Executive Report implementation (ADR-0033) | [m10 3 4 executive report](2026-09-17-m10-3-4-executive-report.md) |
| 2026-09-17 | M11-A: contract-alignment remediation (blind-recomputation boundary) | [m11 a contract alignment remediation](2026-09-17-m11-a-contract-alignment-remediation.md) |
| 2026-09-17 | M11-A: Verification and finalisation contract | [m11 a verification finalisation contract](2026-09-17-m11-a-verification-finalisation-contract.md) |
| 2026-09-17 | M11 `biq-data-profiler` contract / architecture review | [m11 data profiler contract](2026-09-17-m11-data-profiler-contract.md) |
| 2026-09-17 | M11 `biq-data-profiler` implementation | [m11 data profiler implementation](2026-09-17-m11-data-profiler-implementation.md) |
| 2026-09-17 | M11: Verification and finalisation | [m11 verification finalisation](2026-09-17-m11-verification-finalisation.md) |
| 2026-09-17 | M12-A connector layer contract / architecture review | [m12 a connector layer contract](2026-09-17-m12-a-connector-layer-contract.md) |
| 2026-09-17 | M12-A connector layer contract accepted | [m12 a contract acceptance](2026-09-17-m12-a-contract-acceptance.md) |
| 2026-09-17 | M12-A contract remediation: trust chain, layer separation, ADR-0004 relationship | [m12 a contract remediation](2026-09-17-m12-a-contract-remediation.md) |
| 2026-09-18 | M12-A.1 optional connector / user-initiated connection contract | [m12 a1 optional connector lifecycle](2026-09-18-m12-a1-optional-connector-lifecycle.md) |
| 2026-09-18 | M12-B connector registry and value-free discovery catalogue | [m12 b connector registry](2026-09-18-m12-b-connector-registry.md) |
| 2026-09-18 | M13.1 contract conformance: ADR-0040, the owner-accepted environment-unavailable gap | [m13 1 contract conformance adr 0040](2026-09-18-m13-1-contract-conformance-adr-0040.md) |
| 2026-09-18 | M13.1: deterministic hardening | [m13 1 deterministic hardening](2026-09-18-m13-1-deterministic-hardening.md) |
| 2026-09-18 | M13.1 final remediation: U-1 resolved, defect disposition verified, regression re-timed | [m13 1 final remediation](2026-09-18-m13-1-final-remediation.md) |
| 2026-09-18 | M13 contract finalization: ADR-0039 clarified and accepted | [m13 contract finalization](2026-09-18-m13-contract-finalization.md) |
| 2026-09-18 | Post-M12-B roadmap reconciliation and next-milestone contract gate | [post m12b roadmap gate](2026-09-18-post-m12b-roadmap-gate.md) |
| 2026-09-19 | M13.2: ADR-0041 accepted and checkpointed | [m13 2 adr 0041 acceptance](2026-09-19-m13-2-adr-0041-acceptance.md) |
| 2026-09-19 | M13.2 completion-gate preparation: §E.1 outcome (c) recorded, G-2 resolved, G-3 open | [m13 2 e1 outcome g2](2026-09-19-m13-2-e1-outcome-g2.md) |
| 2026-09-19 | M13.2: behavioural eval suite, eval input fixtures and static validator (implementation only) | [m13 2 eval implementation](2026-09-19-m13-2-eval-implementation.md) |
| 2026-09-19 | M13.2 G-1 contract remediation: ADR-0041, deterministic repository-owned eval input fixtures | [m13 2 g1 contract remediation adr 0041](2026-09-19-m13-2-g1-contract-remediation-adr-0041.md) |
| 2026-09-19 | M13.2: manual observation execution pack (preparation only) | [m13 2 manual observation pack](2026-09-19-m13-2-manual-observation-pack.md) |
| 2026-09-19 | M13.2 WD-1 investigation: the engine entry is working-directory-relative (M13-DEF-04) | [m13 2 wd1 investigation](2026-09-19-m13-2-wd1-investigation.md) |
| 2026-09-19 | M13-DEF-04 ADR-0042 Acceptance | [m13 def 04 adr 0042 acceptance](2026-09-19-m13-def-04-adr-0042-acceptance.md) |
| 2026-09-19 | M13-DEF-04 remediation design investigation (design only) | [m13 def 04 remediation design](2026-09-19-m13-def-04-remediation-design.md) |
| 2026-09-19 | M13-DEF-04 Runtime Verification — V-1 / V-2 | [m13 def 04 runtime verification](2026-09-19-m13-def-04-runtime-verification.md) |
| 2026-09-20 | M13.2 §E.1: first controlled evaluation execution (attempted, refused) | [m13 2 e1 execution](2026-09-20-m13-2-e1-execution.md) |
| 2026-09-20 | M13.2 §E.1 first execution: G-3 pre-flight done, execution stopped at the §F.1 ceiling | [m13 2 e1 preflight and stop](2026-09-20-m13-2-e1-preflight-and-stop.md) |
| 2026-09-20 | M13-DEF-04 remediation: the ADR-0042 engine launcher (implementation) | [m13 def 04 implementation](2026-09-20-m13-def-04-implementation.md) |
| 2026-09-20 | M13-DEF-04 Status Governance Reconciliation | [m13 def 04 status governance](2026-09-20-m13-def-04-status-governance.md) |
| 2026-09-22 | M13.2 evaluation-harness remediation: the case can reach its input, and what still stops it | [m13 2 eval harness remediation](2026-09-22-m13-2-eval-harness-remediation.md) |
| 2026-09-22 | M13.2 Stage 2 controlled pilot: one run, refused before turn 1 | [m13 2 stage2 pilot](2026-09-22-m13-2-stage2-pilot.md) |
| 2026-09-22 | ADR-0044 stage 3 from the pilot trace, and M13-DEF-10 | [m13 2 stage3 and grant defect](2026-09-22-m13-2-stage3-and-grant-defect.md) |
| 2026-09-22 | ADR-0044 accepted; Phase 1 of the eval-format migration | [m13 def 05 adr 0044 phase1](2026-09-22-m13-def-05-adr-0044-phase1.md) |
| 2026-09-22 | M13-DEF-05: the platform case contract, established; remediation designed, not performed | [m13 def 05 investigation](2026-09-22-m13-def-05-investigation.md) |
| 2026-09-22 | M13-DEF-06 remediation: a result is admissible only if its run executed | [m13 def 06 remediation](2026-09-22-m13-def-06-remediation.md) |
| 2026-09-22 | M13-DEF-08: a BusinessIQ-owned runtime resolver, so no command names an interpreter | [m13 def 08 runtime resolution](2026-09-22-m13-def-08-runtime-resolution.md) |
| 2026-09-23 | §F.6 scaffold coverage: the remaining 37 business-file cases stage their fixtures | [f6 scaffold coverage](2026-09-23-f6-scaffold-coverage.md) |
| 2026-09-23 | K.4 repair: LF restored in 59 tracked files, and a stale index lock recorded | [k4 line ending repair](2026-09-23-k4-line-ending-repair.md) |
| 2026-09-23 | Final pre-flight: M13-DEF-11 closed, M13-DEF-12 found before any spend | [m13 2 final preflight](2026-09-23-m13-2-final-preflight.md) |
| 2026-09-23 | M13-DEF-10: the evaluation grant set gains `Read`, and the resolver grant is untouched | [m13 def 10 remediation](2026-09-23-m13-def-10-remediation.md) |
| 2026-09-23 | M13-DEF-11: nested sandboxing, diagnosed without an evaluation | [m13 def 11 environment diagnosis](2026-09-23-m13-def-11-environment-diagnosis.md) |
| 2026-09-23 | M13-DEF-12: under WSL, the automatic resolver stops choosing Windows Python | [m13 def 12 remediation](2026-09-23-m13-def-12-remediation.md) |
| 2026-09-25 | M13-DEF-17, M13-DEF-19 and M13-DEF-23: ADR-0047, ADR-0048 and judge-split restructuring | [m13 2 adr 0047 0048 remediation](2026-09-25-m13-2-adr-0047-0048-remediation.md) |
| 2026-09-25 | M13.2 closing evaluation: recording and closure assessment | [m13 2 closing evaluation record](2026-09-25-m13-2-closing-evaluation-record.md) |
| 2026-09-25 | M13-DEF-17 to M13-DEF-23: evaluation grader-contract remediation | [m13 2 grader contract remediation](2026-09-25-m13-2-grader-contract-remediation.md) |
| 2026-09-25 | M13.2 controlled re-evaluation of the 34 corrected cases | [m13 2 reevaluation 34 cases](2026-09-25-m13-2-reevaluation-34-cases.md) |
| 2026-09-25 | M13-DEF-23: ADR-0049, semantic judge splits are `execution_unavailable` | [m13 def 23 adr 0049](2026-09-25-m13-def-23-adr-0049.md) |
| 2026-09-26 | M13.2 availability-completion evaluation of ten routing cases | [m13 2 availability completion](2026-09-26-m13-2-availability-completion.md) |
| 2026-09-26 | M13.2 documentation closure and R-01 resolution | [m13 2 documentation closure](2026-09-26-m13-2-documentation-closure.md) |
| 2026-09-26 | M13.2 owner acceptance and final Git checkpoint | [m13 2 owner acceptance](2026-09-26-m13-2-owner-acceptance.md) |
| 2026-09-26 | M13-DEF-13 remediation: the provenance-aware research boundary | [m13 def 13 remediation](2026-09-26-m13-def-13-remediation.md) |
| 2026-09-26 | M13-DEF-24 PreToolUse hook runtime feasibility experiment | [m13 def 24 hook runtime experiment](2026-09-26-m13-def-24-hook-runtime-experiment.md) |
| 2026-09-26 | M13-DEF-24 remediation: investigation, and why no fix was made | [m13 def 24 investigation](2026-09-26-m13-def-24-investigation.md) |
| 2026-09-26 | M13-DEF-24 live approval-grant verification (ADR-0051) | [m13 def 24 live grant verification](2026-09-26-m13-def-24-live-grant-verification.md) |
| 2026-09-26 | M13-DEF-24 remediation: a pre-execution write-approval boundary (ADR-0051) | [m13 def 24 remediation](2026-09-26-m13-def-24-remediation.md) |
| 2026-09-27 | M14 entry and M14-1: entry and status reconciliation | [m14 1 entry reconciliation](2026-09-27-m14-1-entry-reconciliation.md) |
| 2026-09-27 | M14-2: `README.md` redesign | [m14 2 readme redesign](2026-09-27-m14-2-readme-redesign.md) |
| 2026-09-27 | M14-3: component documentation and index reconciliation | [m14 3 component documentation](2026-09-27-m14-3-component-documentation.md) |
| 2026-09-27 | M14-4: release readiness and finalization | [m14 4 release readiness](2026-09-27-m14-4-release-readiness.md) |
| 2026-09-27 | M14-5: final product corrections and release gate | [m14 5 final product corrections](2026-09-27-m14-5-final-product-corrections.md) |
| 2026-09-27 | M14-6: M9 smoke-test protocol remediation and final release-gate verification | [m14 6 m9 smoke protocol remediation](2026-09-27-m14-6-m9-smoke-protocol-remediation.md) |
| 2026-09-28 | M15: final release-preparation audit | [m15 release preparation audit](2026-09-28-m15-release-preparation-audit.md) |
| 2026-09-28 | M15-1: 0.1.0 release-candidate checkpoint | [m15 1 release candidate checkpoint](2026-09-28-m15-1-release-candidate-checkpoint.md) |
| 2026-09-30 | BusinessOps M1: product identity and technical namespace migration | [businessops m1 identity migration](2026-09-30-businessops-m1-identity-migration.md) |
| 2026-09-30 | BusinessOps M2: Claude Marketplace readiness, governance and packaging audit | [businessops m2 marketplace readiness audit](2026-09-30-businessops-m2-marketplace-readiness-audit.md) |
| 2026-09-30 | BusinessOps M3: packaging, policy and marketplace readiness | [businessops m3 packaging policy readiness](2026-09-30-businessops-m3-packaging-policy-readiness.md) |
| 2026-09-30 | BusinessOps M3.1: installed-package runtime verification | [businessops m3 1 installed package verification](2026-09-30-businessops-m3-1-installed-package-verification.md) |
| 2026-09-30 | BusinessOps M4A: final hardening before the first Git commit | [businessops m4a final hardening](2026-09-30-businessops-m4a-final-hardening.md) |
| 2026-09-30 | BusinessOps M4A.1: remove shipped-plugin CLAUDE.md references (BOPS-R14; work done 2026-10-01) | [businessops m4a1 remove shipped claude md references](2026-09-30-businessops-m4a1-remove-shipped-claude-md-references.md) |
| 2026-10-01 | BusinessOps M4: distribution repository preparation (package built and validated) | [businessops distribution repository preparation](2026-10-01-businessops-distribution-repository-preparation.md) |
