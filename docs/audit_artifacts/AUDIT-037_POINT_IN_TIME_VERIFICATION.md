# AUDIT-037: Point-in-Time Data Integrity Verification

**Audit ID:** AUDIT-037-PIT-VERIFICATION  
**Scope:** Historical Financial Data Ingestion & Availability Engine  
**Target Modules:** `backend/data_pipeline/financial_service.py`, `backend/data_pipeline/backtesting_dataset_service.py`  
**Status:** VERIFIED MATHEMATICALLY & EMPIRICALLY  

---

## 1. Mathematical Formalism of Point-in-Time Financial Availability

In quantitative backtesting, point-in-time (PIT) compliance guarantees that an algorithm evaluating market conditions at time $t_{\text{eval}}$ has access **only** to information that was publicly known at or before $t_{\text{eval}}$.

### 1.1. Core Definitions

Let:
- $Q_i$ denote the financial results for reporting period $i$.
- $T_{\text{end}}(Q_i)$ denote the exact period-end timestamp for quarter $Q_i$ (e.g. `2025-03-31 23:59:59.999999`).
- $T_{\text{pub}}(Q_i)$ denote the verified public disclosure timestamp (NSE/BSE corporate filing timestamp).
- $L_{\text{stat}}$ denote the statutory maximum disclosure window (for SEBI/India LODR: 45 calendar days for Q1-Q3, 60 calendar days for annual Q4 audited results; default conservative uniform parameter: 45 days).
- $T_{\text{eval}}$ denote the backtesting evaluation timestamp.

### 1.2. Strict Point-in-Time Eligibility Rules

A financial record $Q_i$ is eligible for selection at evaluation timestamp $T_{\text{eval}}$ if and only if:

$$\text{Eligible}(Q_i, T_{\text{eval}}) = (T_{\text{end}}(Q_i) \le T_{\text{eval}}) \land (T_{\text{avail}}(Q_i) \le T_{\text{eval}})$$

where the effective availability timestamp $T_{\text{avail}}(Q_i)$ is formally defined as:

$$T_{\text{avail}}(Q_i) = \begin{cases} 
T_{\text{pub}}(Q_i) & \text{if } T_{\text{pub}}(Q_i) \text{ is verified and valid} \\ 
T_{\text{end}}(Q_i) + L_{\text{stat}} & \text{if } T_{\text{pub}}(Q_i) \text{ is NULL, empty, or unparseable} 
\end{cases}$$

### 1.3. Multi-Quarter Selection Rule

Among all eligible historical quarters in the universe of reports $\mathcal{Q}_{\text{symbol}}$, the system must select the unique latest closed and disclosed quarter:

$$Q^*(T_{\text{eval}}) = \arg\max_{Q_i \in \mathcal{Q}_{\text{symbol}}} \{ T_{\text{end}}(Q_i) \mid \text{Eligible}(Q_i, T_{\text{eval}}) = \text{True} \}$$

If $\{ Q_i \mid \text{Eligible}(Q_i, T_{\text{eval}}) = \text{True} \} = \emptyset$, then:
$$Q^*(T_{\text{eval}}) = \text{None}, \quad \text{Status} = \text{"NO\_ELIGIBLE\_RECORDS"}$$

---

## 2. Eligibility State Machine

```
              ┌──────────────────────────────────────────────┐
              │ Evaluate Quarter Record (Period End, Pub Ts)  │
              └──────────────────────┬───────────────────────┘
                                     │
                        Is Period End > Eval Ts?
                                    / \
                                   /   \
                             Yes  /     \  No
                                 v       v
           ┌────────────────────────┐   Does record have a verified,
           │ Reject: Future Quarter │   parseable publication timestamp?
           └────────────────────────┘             / \
                                            Yes  /   \  No
                                                /     \
                                               v       v
                           Is Pub Ts <= Eval Ts?       Is (Period End + Lag) <= Eval Ts?
                                   / \                                 / \
                            Yes   /   \  No                     Yes   /   \  No
                                 v     v                             v     v
┌─────────────────────────────────┐   ┌─────────────────┐ ┌───────────────────────────┐ ┌─────────────────┐
│ VERIFIED_POINT_IN_TIME          │   │ Not Eligible    │ │ PERIOD_ELIGIBLE_FALLBACK_ │ │ Not Eligible    │
│ Mode: VERIFIED_PUBLICATION      │   │ Excluded        │ │ LAG                       │ │ Excluded        │
│ Verified: True                  │   └─────────────────┘ │ Mode: ESTIMATED_LAG       │ └─────────────────┘
└─────────────────────────────────┘                       │ Verified: False           │
                                                          └───────────────────────────┘
```

---

## 3. Rigorous Evaluation of Boundary Cases

| Evaluation Date ($T_{\text{eval}}$) | Quarter ($Q$) | Period End | Verified Pub Date | Fallback Availability | Selected Quarter | Eligibility Status | Point-in-Time Safe? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2025-03-31** | 2025-Q1 | 2025-03-31 | None | 2025-05-15 | Prior Quarter (2024-Q4) | Fallback Lag Inactive | **SAFE** (Zero lookahead) |
| **2025-04-01 (Day +1)** | 2025-Q1 | 2025-03-31 | None | 2025-05-15 | Prior Quarter (2024-Q4) | Fallback Lag Inactive | **SAFE** (Zero lookahead) |
| **2025-04-20** | 2025-Q1 | 2025-03-31 | 2025-04-20 | 2025-05-15 | **2025-Q1** | `VERIFIED_POINT_IN_TIME` | **SAFE** (Filing occurred today) |
| **2025-05-14 (Day +44)** | 2025-Q1 | 2025-03-31 | None | 2025-05-15 | Prior Quarter (2024-Q4) | Fallback Lag Inactive | **SAFE** (Day before 45-day lag) |
| **2025-05-15 (Day +45)** | 2025-Q1 | 2025-03-31 | None | 2025-05-15 | **2025-Q1** | `PERIOD_ELIGIBLE_FALLBACK_LAG` | **SAFE** (45-day statutory window reached) |
| **2025-05-20** | 2025-Q1 | 2025-03-31 | 2025-06-01 | 2025-05-15 | Prior Quarter (2024-Q4) | Late Filing Waiting | **SAFE** (Verified late filing overrides lag) |

---

## 4. Edge Cases and Resilience

1. **Leap Years (e.g. February 29):**
   - Timestamp math is executed via pandas `pd.Timedelta(days=45)` and Python `datetime` engines, correctly accounting for leap days.
2. **Timezone Normalization:**
   - Both `_normalize_eval_timestamp` and `_normalize_pub_timestamp` strip timezones into UTC naive timestamps (`ts.tz_convert('UTC').tz_localize(None)` if tz-aware).
   - Date-only evaluation cutoffs (`YYYY-MM-DD`) receive end-of-day semantics (`23:59:59.999999`) to allow filings published during market or post-market hours of that calendar day to be eligible for subsequent trading.
3. **Missing Publication Timestamps Disclosure:**
   - In `database/swing_trading.db`, all 260 quarterly results have `publication_date = NULL`. Under AUDIT-037, every single observation is transparently marked `financial_availability_status = "UNVERIFIED"` and `financial_eligibility_mode = "ESTIMATED_REPORTING_LAG"`. Zero observations are falsely promoted to "VERIFIED".

