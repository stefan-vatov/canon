# Project Overview

This project is an in-memory inventory reservation library used by checkout
tooling. It tracks stock levels per sku and accumulates reservations against
them. There is no persistence and no I/O. The single domain is
[inventory](inventory/overview.md).
