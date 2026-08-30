# Week 12 — Database Backup & Recovery Operations

## 1. Purpose

This document defines the backup, restore, recovery validation, and operational
procedure for the Swing Trading Intelligence Platform database.

The procedure protects the validated Data Engineering data without modifying
trading logic, scoring logic, or frontend functionality.

---

## 2. Production Database

Database type:

- SQLite

Production database:

```text
database/swing_trading.db