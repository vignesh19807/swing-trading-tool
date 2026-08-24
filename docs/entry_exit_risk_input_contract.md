# Week 8 — Entry / Exit & Risk Input Contract

## Swing Trading Intelligence Platform

**Owner:** Data Engineering  
**Consumer:** Logic / Risk Engineering  
**Status:** Validated  
**Week:** 8

---

## 1. Purpose

This document defines the standardized data contract between the
Data Engineering layer and the Logic / Risk Engine.

The Data Engineering layer provides market-derived inputs.

The Logic / Risk Engine is responsible for applying trading rules,
risk rules, signal qualification, and final trading decisions.

### Data Engineering MUST NOT

- Generate BUY/SELL decisions
- Perform final signal qualification
- Decide whether a setup is tradable
- Perform position sizing
- Override risk rules

---

# 2. Data Flow

```text
Daily OHLCV
     |
     v
Data Service
     |
     v
Technical Engine
     |
     +----------------------+
     |                      |
     v                      v
Technical Indicators    Support/Resistance
     |                      |
     +----------+-----------+
                |
                v
       Entry/Exit Input Service
                |
                v
       Stop/Target Input Service
                |
                v
        Logic / Risk Engine