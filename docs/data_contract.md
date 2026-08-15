# Data Service Contract

## Purpose

This document defines the interface between the Data Engineering layer
and the Logic Engineering layer of the Swing Trading Intelligence Platform.

The Data Engineer is responsible for collecting, validating, storing,
and serving reliable market data.

The Logic Engineer consumes the data through the Data Service and
does not need to access SQLite or write SQL queries directly.

---

# 1. Data Access

The Logic Engineer should access market data through:

```python
from backend.data_pipeline.data_service import get_stock_data

data = get_stock_data("INFY")