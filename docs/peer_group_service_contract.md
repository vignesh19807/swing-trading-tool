# Peer Group Service Contract

## Week 7 — Data Engineering → Logic Engineering

This document defines the interface between the Data Engineering
peer-group layer and the Logic Engineering layer.

The Logic Engineer must use these service functions instead of
accessing SQLite directly.

---

## 1. Company Classification

### Function

```python
get_company_classification(symbol)