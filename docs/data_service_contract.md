# Week 5 — Data Service Contract

## Purpose

This document defines the interface between the Data Engineering
layer and the Logic Engineering layer.

The Logic Engineer should access market and financial information
through the Data Services rather than directly accessing external
providers or the SQLite database.

---

# 1. Market Data Service

## Function

```python
get_stock_data(symbol)