# Exploratory Sandbox Policy After Data Regime Stop

This policy defines the allowed research sandbox after `current_data_regime_research_stopped`.

The governance goal is to add an explicit allowed zone for understanding and documentation. It does not weaken any existing red line, does not restart strategy research, and does not authorize alpha promotion, portfolio work, frozen test access, validation tuning, or trainval-as-OOS claims.

## Core Interpretation

`current_data_regime_research_stop` stops strategy advancement under the current D0 OHLCV + state field regime. It does not stop all research understanding.

The stop decision remains binding for promotion and portfolio use. It means the project has no clean portfolio-ready candidate under the current research question. It does not mean researchers may no longer write paper-only hypotheses, summarize known failure mechanisms, or perform descriptive diagnostics that do not create candidates and do not claim alpha.

## Explicitly Allowed Work

### Paper-Only Work

Paper-only pre-registration is explicitly allowed.

Allowed paper-only work includes:

- drafting a future research question before any implementation;
- defining hypotheses, admissible evidence, success criteria, and stop rules;
- reviewing whether a reframed question is independent from the stopped TopK / mid-rank claim;
- writing governance notes that clarify what would be required before a new phase could start.

Paper-only work must not train, backtest, run portfolio, generate holdings, generate formal metrics/readout, read frozen test, or define concrete trading rules for immediate use.

### Descriptive Mechanism Work

Descriptive mechanism research is allowed.

Allowed descriptive work may use existing train/validation research evidence only to understand mechanisms, failure modes, and research boundaries. It may describe what happened in prior artifacts, recompute descriptive summaries where needed, and prepare future questions. It must not promote an alpha, produce a candidate, or claim deployability.

Allowed descriptive mechanism questions include:

- rank-band full profile;
- market-state conditional diagnostics;
- long/short asymmetry;
- cross-model agreement/disagreement;
- feature interaction description;
- failure mechanism summary.

These questions are allowed because they improve understanding of the stopped regime. They are not allowed because they can be used to bypass the stop decision.

## Four Governance Levels

The project uses four governance levels after the data regime stop:

| level | status | allowed output | prohibited output |
| --- | --- | --- | --- |
| paper-only | allowed | pre-registration drafts, governance notes, hypothesis definitions | code implementation, training, backtest, portfolio, frozen test access |
| exploratory descriptive | allowed | descriptive mechanism research, failure summaries, non-promotional diagnostics | alpha claims, candidate creation, portfolio dry-run, validation tuning |
| pre-registered implementation | blocked by default | only possible after a separately approved pre-registration for a genuinely reframed problem | implicit restart from current evidence, v4, reusing p98 as a clean gold standard |
| promotion / portfolio | prohibited under current regime | none | portfolio, portfolio dry-run, holdings generation, formal promotion, frozen test access |

## Hard Prohibitions Retained

The exploratory sandbox keeps all existing hard prohibitions:

- no frozen test;
- no portfolio;
- no portfolio dry-run;
- no v4;
- no trainval-as-OOS;
- trainval not OOS;
- no validation tuning;
- no treating `p98` or `multi_equal_weight_v1` as a clean gold standard;
- no alpha claim from descriptive diagnostics;
- no candidate generation from descriptive diagnostics.

Any work that needs frozen test access, portfolio execution, portfolio dry-run, v4, validation-selected rules, or promotion language is outside this sandbox and remains prohibited.

## Candidate And Alpha Boundary

Exploratory descriptive research must not:

- declare alpha;
- name a new candidate;
- modify score formulas to improve validation metrics;
- choose rank bands, thresholds, states, feature interactions, or asymmetry rules because they look favorable in validation;
- run portfolio or portfolio dry-run;
- read frozen test;
- convert trainval diagnostics into OOS claims.

If a descriptive finding suggests a future implementable idea, the only allowed next step is paper-only pre-registration. Implementation requires a separate governance decision and must explain why the new question is not the stopped clean TopK / mid-rank question in another form.

## Listing-Age Repair Boundary

listing_age repair is data-quality remediation.

`listing_age_trading_days` repair is data-quality remediation.

Fixing `listing_age_trading_days` or related field completeness issues belongs to basic data integrity work. It may improve field contracts, completeness audits, or downstream guardrails. It is not alpha research, not a candidate, not a strategy restart, and not authorization for portfolio or frozen test access.

Any later use of repaired listing-age fields must still pass the relevant next-use guardrail and must not be treated as evidence that strategy research has resumed.

## Policy Summary

This policy increases the allowed research zone after `current_data_regime_research_stopped`.

It allows paper-only pre-registration and descriptive mechanism research so the project can keep learning from its existing evidence. It preserves strict promotion boundaries: no alpha claim, no candidate, no portfolio, no portfolio dry-run, no frozen test, no v4, no validation tuning, no trainval-as-OOS, and no p98 as a clean gold standard.
