# Daizzy.online — Inventory Management + Sales + POS System
## Product Development Guide (PDG) & System Architecture v1.0

> **Status**: Architecture Draft · Awaiting Approval  
> **Date**: September 17, 2026  
> **Prepared for**: Daizzy.online  
> **System Codename**: `Daizzy IMS`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Business Goals](#2-business-goals)
3. [MVP Scope](#3-mvp-scope)
4. [Non-MVP Scope](#4-non-mvp-scope)
5. [User Roles](#5-user-roles)
6. [System Architecture](#6-system-architecture)
7. [Django App Architecture](#7-django-app-architecture)
8. [Design Patterns](#8-design-patterns)
9. [Domain Model](#9-domain-model)
10. [Database ERD Description](#10-database-erd-description)
11. [Database Tables](#11-database-tables)
12. [Relationships](#12-relationships)
13. [Inventory Ledger Design](#13-inventory-ledger-design)
14. [Stock Consistency Strategy](#14-stock-consistency-strategy)
15. [Barcode Architecture](#15-barcode-architecture)
16. [Hardware Scanner Workflow](#16-hardware-scanner-workflow)
17. [Camera Scanner Workflow](#17-camera-scanner-workflow)
18. [POS Workflow](#18-pos-workflow)
19. [Sales Workflow](#19-sales-workflow)
20. [Return Workflow](#20-return-workflow)
21. [Invoice Workflow](#21-invoice-workflow)
22. [Printing Architecture](#22-printing-architecture)
23. [REST API Architecture](#23-rest-api-architecture)
24. [API Endpoint Specification](#24-api-endpoint-specification)
25. [Authentication / Authorization](#25-authentication--authorization)
26. [Security Architecture](#26-security-architecture)
27. [Audit Logging](#27-audit-logging)
28. [Frontend Architecture](#28-frontend-architecture)
29. [UI/UX Design System](#29-uiux-design-system)
30. [Page-by-Page UI Specification](#30-page-by-page-ui-specification)
31. [Component Architecture](#31-component-architecture)
32. [Error Handling](#32-error-handling)
33. [Validation Rules](#33-validation-rules)
34. [Reporting](#34-reporting)
35. [Performance](#35-performance)
36. [Testing Strategy](#36-testing-strategy)
37. [Deployment Architecture](#37-deployment-architecture)
38. [Backup Strategy](#38-backup-strategy)
39. [Development Roadmap](#39-development-roadmap)
40. [Recommended Project Folder Structure](#40-recommended-project-folder-structure)
41. [Recommended Dependencies](#41-recommended-dependencies)
42. [Future Extension Points](#42-future-extension-points)
43. [Risks and Mitigations](#43-risks-and-mitigations)
44. [Final Architecture Summary](#44-final-architecture-summary)

---

## 1. Executive Summary

**Daizzy IMS** is a production-grade, modular Inventory Management + Sales + POS system built on Django. It serves as the operational backbone for Daizzy.online — managing every product, every barcode, every stock movement, every sale, and every invoice from one centralized, authoritative system.

The system exposes a REST API that allows the public-facing Daizzy.online website (and any future external application) to query products, check stock, and create orders — while the internal management UI is used by staff, cashiers, and managers.

**Core philosophy**:
- The **backend is the single source of truth** for price, stock, permissions, and sale validity.
- Every stock change is **auditable and traceable**.
- The **POS is optimized for speed** — a cashier should complete a sale with minimal clicks.
- The **barcode is a first-class citizen** — not an afterthought.

---

## 2. Business Goals

| Priority | Goal |
|----------|------|
| 🔴 Critical | Track product inventory accurately in real time |
| 🔴 Critical | Enable fast, reliable POS sales with barcode scanning |
| 🔴 Critical | Generate and print invoices immediately after sale |
| 🔴 Critical | Maintain an auditable inventory ledger for every stock movement |
| 🟠 High | Expose REST API for Daizzy.online website integration |
| 🟠 High | Support hardware and camera barcode scanning |
| 🟠 High | Enable sales returns with proper inventory restoration |
| 🟡 Medium | Provide operational reports: sales, stock, low stock |
| 🟡 Medium | Manage user roles and permissions server-side |
| 🟢 Future | Multi-store support, advanced analytics, procurement |

---

## 3. MVP Scope

The following modules are **in scope** for the MVP:

| Module | Description |
|--------|-------------|
| **User Management** | Authentication, roles, permissions |
| **Product Management** | Create, edit, categorize, search products |
| **Barcode Management** | Generate, assign, validate, print barcodes |
| **Inventory Management** | Stock tracking, adjustments, ledger |
| **POS** | Cart, barcode scan, payment, checkout |
| **Sales Management** | Sale records, history, search |
| **Invoice Management** | Generation, print, reprint |
| **Returns** | Return workflow, inventory restoration |
| **REST API** | Products, inventory, sales, invoice endpoints |
| **Reports** | Sales summary, inventory status, low stock |
| **Audit Logging** | Track all critical business actions |
| **Store Settings** | Configurable store info, invoice prefix, policies |

---

## 4. Non-MVP Scope

The following are **explicitly excluded** from MVP to maintain focus:

- ❌ HR / Payroll / Timesheets
- ❌ Full Accounting / Double-entry bookkeeping
- ❌ CRM / Customer loyalty programs
- ❌ Procurement / Purchase orders / Supplier management
- ❌ Manufacturing / BOM
- ❌ Multi-warehouse management
- ❌ AI forecasting / Demand planning
- ❌ Offline-first POS with sync (architecture prepared, not implemented)
- ❌ ESC/POS direct USB printing (browser print used first)
- ❌ Payment gateway integration (manual payment recording only in MVP)

> [!NOTE]
> These are **extension points**, not limitations. The architecture is designed so any of these can be added without restructuring the core system.

---

## 5. User Roles

Permissions are enforced **server-side** using Django's permission system extended with role-based access control (RBAC). Frontend hiding is a UX convenience only — never the security boundary.

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| `SUPER_ADMIN` | Full system access | All permissions + system settings |
| `ADMIN` | Full business access | All except system-level settings |
| `MANAGER` | Manage operations | Products, inventory, sales, reports, users (limited) |
| `INVENTORY_MANAGER` | Inventory specialist | Products, stock, barcodes, adjustments |
| `CASHIER` | POS operator | POS, sales, view products |
| `STAFF` | General staff | View products, view sales |

### Permission Matrix (key actions)

| Action | SUPER_ADMIN | ADMIN | MANAGER | INV_MGR | CASHIER | STAFF |
|--------|:-----------:|:-----:|:-------:|:-------:|:-------:|:-----:|
| Create/Edit Products | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Delete/Deactivate Products | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Stock Adjustments | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| POS / Create Sales | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| Cancel Sales | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Process Returns | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| View Reports | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Manage Users | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| System Settings | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Reprint Invoice | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |

---

## 6. System Architecture

### Architecture Decision: Modular Monolith

**Chosen**: Modular Monolith on Django  
**Rejected**: Microservices

**Rationale**: For a small-to-medium business internal system, microservices introduce deployment complexity, distributed transaction problems, and network overhead without meaningful benefit. A well-structured Django modular monolith is:
- Easier to develop and debug
- Transactionally consistent (single database)
- Simpler to deploy (one process + Gunicorn)
- Easier to refactor into services later if needed
- Faster for the team to iterate

If Daizzy.online later scales to multiple warehouses or needs independent deployments, specific bounded contexts (e.g., the REST API) can be extracted without redesigning the core.

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERNET                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────────────────┐
│                    NGINX (Reverse Proxy)                          │
│              Static Files · SSL Termination                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│              GUNICORN (Django Application Server)                 │
│                                                                   │
│   ┌─────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│   │  Web UI     │  │  REST API     │  │  Admin               │  │
│   │  (Django    │  │  /api/v1/     │  │  /admin/             │  │
│   │  Templates) │  │  (DRF)        │  │  (Django Admin)      │  │
│   └─────────────┘  └───────────────┘  └──────────────────────┘  │
│                                                                   │
│   ┌───────────────────────────────────────────────────────────┐  │
│   │                  SERVICE LAYER                             │  │
│   │  ProductService · InventoryService · SaleService          │  │
│   │  BarcodeService · InvoiceService · ReportService          │  │
│   └───────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    POSTGRESQL DATABASE                            │
└─────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│               MEDIA STORAGE (Local / S3-compatible)              │
└─────────────────────────────────────────────────────────────────┘
```

### External Integrations

```
Daizzy.online Website ──────► REST API (/api/v1/)
External Apps           ──────► REST API (/api/v1/)
Barcode Hardware Scanner ────► Browser Keyboard Input → POS
Device Camera            ────► JS Barcode Library → POS
Printer                  ────► Browser Print / CSS @media print
```

---

## 7. Django App Architecture

### Project Structure

```
daizzy_ims/                          ← Project root
│
├── config/                          ← Django configuration
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                  ← Shared settings
│   │   ├── development.py           ← Dev overrides
│   │   └── production.py            ← Production overrides
│   ├── urls.py                      ← Root URL configuration
│   ├── asgi.py
│   └── wsgi.py
│
├── apps/                            ← All Django applications
│   │
│   ├── core/                        ← Shared abstractions
│   │   ├── models.py                ← TimeStampedModel, SoftDeleteModel
│   │   ├── permissions.py           ← Role-based permission classes
│   │   ├── exceptions.py            ← Custom exception types
│   │   ├── mixins.py                ← Common mixins
│   │   ├── pagination.py            ← Standard pagination
│   │   ├── validators.py            ← Shared validators
│   │   └── utils.py                 ← Shared utilities
│   │
│   ├── users/                       ← Authentication & user management
│   │   ├── models.py                ← User, Role
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── services.py              ← UserService
│   │
│   ├── products/                    ← Product catalog
│   │   ├── models.py                ← Product, Category
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── services.py              ← ProductService
│   │   └── filters.py               ← Product filtering
│   │
│   ├── inventory/                   ← Stock management
│   │   ├── models.py                ← Inventory, InventoryTransaction
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── services.py              ← InventoryService, StockAdjustmentService
│   │
│   ├── barcode/                     ← Barcode lifecycle
│   │   ├── models.py                ← BarcodeConfig (optional)
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── services.py              ← BarcodeService
│   │   ├── generators.py            ← Strategy: barcode generation
│   │   └── printers.py              ← Label generation
│   │
│   ├── sales/                       ← Sales transactions
│   │   ├── models.py                ← Sale, SaleItem, Payment
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── services.py              ← SaleService, ReturnService
│   │
│   ├── pos/                         ← POS-specific views
│   │   ├── views.py                 ← POS screen view
│   │   └── urls.py
│   │
│   ├── invoices/                    ← Invoice management
│   │   ├── models.py                ← Invoice
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── services.py              ← InvoiceService
│   │   └── numbering.py             ← Invoice number strategy
│   │
│   ├── reports/                     ← Reporting module
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── services.py              ← ReportService
│   │
│   ├── settings_app/                ← Business settings
│   │   ├── models.py                ← StoreSettings, POSSettings
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   │
│   ├── audit/                       ← Audit trail
│   │   ├── models.py                ← AuditLog
│   │   ├── mixins.py                ← AuditMixin
│   │   └── services.py              ← AuditService
│   │
│   └── api/                         ← API root + versioning
│       ├── v1/
│       │   └── urls.py              ← All /api/v1/ routes
│       └── urls.py
│
├── templates/                       ← Django HTML templates
│   ├── base/
│   │   ├── base.html
│   │   ├── base_auth.html
│   │   └── base_print.html
│   ├── dashboard/
│   ├── products/
│   ├── inventory/
│   ├── pos/
│   ├── sales/
│   ├── invoices/
│   ├── barcode/
│   ├── reports/
│   └── settings/
│
├── static/
│   ├── css/
│   │   ├── main.css                 ← Design tokens + base styles
│   │   ├── components.css           ← Reusable component styles
│   │   ├── pos.css                  ← POS-specific layout
│   │   └── print.css                ← @media print styles
│   ├── js/
│   │   ├── core.js                  ← Utilities, toast, AJAX helpers
│   │   ├── pos.js                   ← POS cart, barcode input
│   │   ├── barcode-scanner.js       ← Camera scanner integration
│   │   └── barcode-label.js         ← Label preview/print
│   └── images/
│
├── media/                           ← Uploaded media (gitignored)
│
├── tests/
│   ├── test_products.py
│   ├── test_inventory.py
│   ├── test_sales.py
│   ├── test_barcode.py
│   ├── test_api.py
│   └── test_concurrency.py
│
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── .env.example
├── manage.py
├── Dockerfile
├── docker-compose.yml
└── README.md
```

**Why the `apps/core` module?** — It prevents every app from reimplementing `created_at`, `updated_at`, soft delete, and permission logic. Every model inherits from `TimeStampedModel`. Role permission checks are imported from one place.

**Why separate `pos/` from `sales/`?** — The POS is a UI concern: the screen, the keyboard shortcuts, the camera scanner. The Sales app is a domain concern: the data, the business rules, the service layer. Keeping them separate allows the sales logic to be reused by the API without coupling it to POS-specific views.

**Why a separate `api/` router?** — Clean versioning (`/api/v1/`, `/api/v2/`) without contaminating the individual app URL files.

---

## 8. Design Patterns

### Service Layer Pattern ✅ (Primary pattern)

Business logic lives in `services.py` files inside each app — **never in views, never in serializers, never in models** (beyond basic validation).

```
View/Serializer  →  Service  →  Model/ORM
```

| Service | Responsibilities |
|---------|-----------------|
| `ProductService` | Create/update products, validate SKU/barcode uniqueness, handle image processing |
| `BarcodeService` | Generate barcodes, validate uniqueness, generate printable images, batch generation |
| `InventoryService` | Query stock, record opening stock, stock overview |
| `StockAdjustmentService` | Apply adjustments, create ledger entries, validate adjustment rules |
| `SaleService` | Create sale, validate cart, lock stock, create items, trigger invoice, deduct inventory |
| `ReturnService` | Validate return quantity, restore inventory, record refund, create return ledger entries |
| `PaymentService` | Record payment, validate payment amounts, future: gateway integration |
| `InvoiceService` | Generate invoice number, create invoice record, generate print HTML |
| `ReportService` | Aggregate sales, inventory summaries, low-stock queries |
| `AuditService` | Record audit log entries for critical events |

### Strategy Pattern ✅

Used for barcode generation (different formats), payment methods, and invoice rendering.

```python
# barcode/generators.py
class BarcodeGeneratorStrategy(ABC):
    def generate(self, product) -> str: ...

class Code128Generator(BarcodeGeneratorStrategy): ...
class EAN13Generator(BarcodeGeneratorStrategy): ...
class InternalCodeGenerator(BarcodeGeneratorStrategy): ...

class BarcodeService:
    def __init__(self, strategy: BarcodeGeneratorStrategy):
        self.strategy = strategy
    
    def generate_for_product(self, product) -> str:
        code = self.strategy.generate(product)
        self._validate_uniqueness(code)
        return code
```

This means the business can switch from internal codes to EAN-13 without rewriting the service.

### Factory Pattern ✅

Used for payment handler creation and invoice format rendering.

```python
class PaymentHandlerFactory:
    handlers = {
        'CASH': CashPaymentHandler,
        'BKASH': BkashPaymentHandler,
        'CARD': CardPaymentHandler,
    }
    
    @classmethod
    def get_handler(cls, method: str) -> BasePaymentHandler:
        return cls.handlers[method]()
```

### Adapter Pattern ✅

Critical for external website integration. The REST API acts as an adapter between Daizzy.online's website and the internal business logic.

Future adapters: ESC/POS printer adapter, external payment gateway adapter.

### Unit of Work / Transaction Pattern ✅

All multi-step business operations that must be atomic use `transaction.atomic()`:

```python
# sales/services.py
def complete_sale(self, cart_data, payment_data, cashier):
    with transaction.atomic():
        # Lock rows, validate, create sale, deduct stock, create invoice
        ...
```

`select_for_update()` is used specifically for inventory row locking during sales. See Section 14.

### Observer / Signal Pattern (Light) ✅

Django signals are used for post-action side effects (audit logging, notifications). They are kept simple — no external message brokers in MVP.

```python
# Signal: after sale completes → trigger audit log
post_save.connect(audit_sale_created, sender=Sale)
```

### Soft Delete Pattern ✅

`is_active` flag used on products and categories. History is never destroyed.

---

## 9. Domain Model

### Core Domain Entities

```
┌─────────┐     ┌─────────────┐     ┌───────────────┐
│  User   │     │  Category   │     │  StoreSettings│
└────┬────┘     └──────┬──────┘     └───────────────┘
     │                 │
     │         ┌───────▼──────┐
     │         │   Product    │◄─────────────────────┐
     │         │              │                      │
     │         │  SKU         │                      │
     │         │  Barcode     │◄── BarcodeConfig      │
     │         │  Prices      │                      │
     │         └──────┬───────┘                      │
     │                │                              │
     │    ┌───────────▼──────────┐                   │
     │    │  InventoryTransaction│                   │
     │    │  (Ledger)            │                   │
     │    └──────────────────────┘                   │
     │                                               │
     │    ┌──────────┐   ┌──────────┐                │
     └───►│   Sale   │──►│ SaleItem │───────────────►│
          └────┬─────┘   └──────────┘
               │
          ┌────▼─────┐   ┌──────────┐
          │ Payment  │   │ Invoice  │
          └──────────┘   └──────────┘
               │
          ┌────▼──────┐  ┌──────────────────┐
          │  Return   │──►InventoryTransaction│
          └───────────┘  └──────────────────┘
```

### Domain Invariants

1. **One barcode → one active product** (database UNIQUE constraint)
2. **One SKU → one product** (database UNIQUE constraint)
3. **Stock cannot go negative** (enforced by service layer + DB check)
4. **Invoice number is globally unique** (database UNIQUE + atomic generation)
5. **A completed sale is immutable** (status-based, never deleted)
6. **Every stock movement has a ledger entry** (enforced in service layer)
7. **Sale-time prices are frozen** in SaleItem (current product price may change later)

---

## 10. Database ERD Description

The database consists of these primary entity groups:

**User Group**: `users_user` (custom user model)

**Catalog Group**: `products_category` → `products_product` (one-to-many)

**Inventory Group**: `inventory_inventorytransaction` references `products_product`

**Sales Group**: `sales_sale` → `sales_saleitem` (one-to-many), `sales_payment` (one-to-one), `sales_return` → `sales_returnitem` (one-to-many)

**Invoice Group**: `invoices_invoice` (one-to-one with `sales_sale`)

**Audit Group**: `audit_auditlog` (generic reference to any entity)

**Settings Group**: `settings_storesettings`, `settings_possettings`

All tables inherit `created_at` and `updated_at` timestamps from the abstract base model.

---

## 11. Database Tables

### `users_user`

```sql
id              BIGSERIAL PRIMARY KEY
username        VARCHAR(150) UNIQUE NOT NULL
email           VARCHAR(254) UNIQUE NOT NULL
password        VARCHAR(128) NOT NULL       -- bcrypt hashed
first_name      VARCHAR(150)
last_name       VARCHAR(150)
role            VARCHAR(30) NOT NULL        -- SUPER_ADMIN, ADMIN, etc.
is_active       BOOLEAN DEFAULT TRUE
is_staff        BOOLEAN DEFAULT FALSE       -- Django admin access
created_at      TIMESTAMPTZ DEFAULT NOW()
updated_at      TIMESTAMPTZ DEFAULT NOW()
```

**Indexes**: `username`, `email`, `role`, `is_active`

---

### `products_category`

```sql
id                BIGSERIAL PRIMARY KEY
name              VARCHAR(200) NOT NULL
slug              VARCHAR(200) UNIQUE NOT NULL
description       TEXT
image             VARCHAR(500)               -- media path
is_active         BOOLEAN DEFAULT TRUE
display_priority  SMALLINT DEFAULT 0
created_at        TIMESTAMPTZ DEFAULT NOW()
updated_at        TIMESTAMPTZ DEFAULT NOW()
```

**Indexes**: `slug`, `is_active`, `display_priority`

---

### `products_product`

```sql
id                  BIGSERIAL PRIMARY KEY
sku                 VARCHAR(100) UNIQUE NOT NULL
barcode             VARCHAR(100) UNIQUE NOT NULL    -- DB-enforced uniqueness
name                VARCHAR(300) NOT NULL
slug                VARCHAR(300) UNIQUE NOT NULL
category_id         BIGINT REFERENCES products_category(id)
description         TEXT
unit                VARCHAR(50) DEFAULT 'pcs'
cost_price          NUMERIC(12,2) NOT NULL DEFAULT 0
selling_price       NUMERIC(12,2) NOT NULL
discount_price      NUMERIC(12,2)
minimum_stock_level SMALLINT DEFAULT 5
image               VARCHAR(500)
is_active           BOOLEAN DEFAULT TRUE
created_at          TIMESTAMPTZ DEFAULT NOW()
updated_at          TIMESTAMPTZ DEFAULT NOW()
```

**Note on stock quantity**: Stock quantity is **not stored on the product table**. It is derived from the `inventory_inventorytransaction` ledger OR maintained as a cached denormalized value in `inventory_inventory`. See Section 13 for the rationale.

**Indexes**: `barcode` (UNIQUE), `sku` (UNIQUE), `slug` (UNIQUE), `category_id`, `is_active`, `name` (GIN trigram for search)

---

### `inventory_inventory`

```sql
id              BIGSERIAL PRIMARY KEY
product_id      BIGINT UNIQUE REFERENCES products_product(id)
quantity        INTEGER NOT NULL DEFAULT 0
updated_at      TIMESTAMPTZ DEFAULT NOW()
```

**Why a separate Inventory model?** — This allows `select_for_update()` to lock only the inventory row during a sale, without locking the entire product row. It also cleanly separates "product information" from "stock state".

**Indexes**: `product_id` (UNIQUE), `quantity`

---

### `inventory_inventorytransaction`

```sql
id                  BIGSERIAL PRIMARY KEY
product_id          BIGINT NOT NULL REFERENCES products_product(id)
transaction_type    VARCHAR(30) NOT NULL
    -- OPENING_STOCK, PURCHASE, SALE, RETURN,
    -- ADJUSTMENT_IN, ADJUSTMENT_OUT, DAMAGE, LOSS, CORRECTION
quantity            INTEGER NOT NULL          -- always positive
direction           SMALLINT NOT NULL         -- +1 (IN) or -1 (OUT)
previous_quantity   INTEGER NOT NULL
new_quantity        INTEGER NOT NULL
reference_type      VARCHAR(50)               -- 'sale', 'return', 'adjustment'
reference_id        BIGINT                    -- FK to the referencing record
reason              VARCHAR(300)
notes               TEXT
created_by_id       BIGINT REFERENCES users_user(id)
created_at          TIMESTAMPTZ DEFAULT NOW()
```

**Constraint**: `quantity > 0` (CHECK)
**Constraint**: `direction IN (-1, 1)` (CHECK)
**Indexes**: `product_id`, `transaction_type`, `created_at`, `reference_type + reference_id`

---

### `sales_sale`

```sql
id                  BIGSERIAL PRIMARY KEY
invoice_number      VARCHAR(50) UNIQUE NOT NULL
subtotal            NUMERIC(12,2) NOT NULL
discount_amount     NUMERIC(12,2) DEFAULT 0
tax_amount          NUMERIC(12,2) DEFAULT 0
grand_total         NUMERIC(12,2) NOT NULL
amount_paid         NUMERIC(12,2) NOT NULL DEFAULT 0
change_amount       NUMERIC(12,2) DEFAULT 0
payment_status      VARCHAR(20) NOT NULL
    -- PENDING, PAID, PARTIAL, REFUNDED
status              VARCHAR(20) NOT NULL
    -- COMPLETED, CANCELLED, PARTIALLY_RETURNED, RETURNED
cashier_id          BIGINT REFERENCES users_user(id)
customer_name       VARCHAR(200)
customer_phone      VARCHAR(30)
customer_email      VARCHAR(254)
notes               TEXT
created_at          TIMESTAMPTZ DEFAULT NOW()
updated_at          TIMESTAMPTZ DEFAULT NOW()
```

**Indexes**: `invoice_number` (UNIQUE), `status`, `payment_status`, `cashier_id`, `created_at`

---

### `sales_saleitem`

```sql
id              BIGSERIAL PRIMARY KEY
sale_id         BIGINT NOT NULL REFERENCES sales_sale(id)
product_id      BIGINT NOT NULL REFERENCES products_product(id)
product_name    VARCHAR(300) NOT NULL    -- snapshot at sale time
product_sku     VARCHAR(100) NOT NULL    -- snapshot at sale time
product_barcode VARCHAR(100) NOT NULL    -- snapshot at sale time
unit_price      NUMERIC(12,2) NOT NULL   -- snapshot at sale time
discount        NUMERIC(12,2) DEFAULT 0
quantity        SMALLINT NOT NULL
line_total      NUMERIC(12,2) NOT NULL
created_at      TIMESTAMPTZ DEFAULT NOW()
```

**Constraint**: `quantity > 0` (CHECK)
**Constraint**: `unit_price >= 0` (CHECK)
**Indexes**: `sale_id`, `product_id`

**Why snapshot product_name/sku/barcode/unit_price?** — If a product is renamed or its price changes later, historical invoices remain accurate. This is non-negotiable for business integrity.

---

### `sales_payment`

```sql
id                      BIGSERIAL PRIMARY KEY
sale_id                 BIGINT UNIQUE NOT NULL REFERENCES sales_sale(id)
payment_method          VARCHAR(30) NOT NULL
    -- CASH, BKASH, NAGAD, CARD, BANK, OTHER
amount_paid             NUMERIC(12,2) NOT NULL
due_amount              NUMERIC(12,2) DEFAULT 0
change_amount           NUMERIC(12,2) DEFAULT 0
transaction_reference   VARCHAR(200)
payment_status          VARCHAR(20) NOT NULL
notes                   TEXT
created_at              TIMESTAMPTZ DEFAULT NOW()
```

**Indexes**: `sale_id` (UNIQUE), `payment_method`, `payment_status`

---

### `sales_return`

```sql
id                  BIGSERIAL PRIMARY KEY
sale_id             BIGINT NOT NULL REFERENCES sales_sale(id)
processed_by_id     BIGINT REFERENCES users_user(id)
refund_method       VARCHAR(30)
refund_amount       NUMERIC(12,2) DEFAULT 0
reason              VARCHAR(300)
notes               TEXT
status              VARCHAR(20) NOT NULL DEFAULT 'COMPLETED'
created_at          TIMESTAMPTZ DEFAULT NOW()
```

---

### `sales_returnitem`

```sql
id              BIGSERIAL PRIMARY KEY
return_id       BIGINT NOT NULL REFERENCES sales_return(id)
sale_item_id    BIGINT NOT NULL REFERENCES sales_saleitem(id)
product_id      BIGINT NOT NULL REFERENCES products_product(id)
quantity        SMALLINT NOT NULL
unit_price      NUMERIC(12,2) NOT NULL
line_total      NUMERIC(12,2) NOT NULL
created_at      TIMESTAMPTZ DEFAULT NOW()
```

**Constraint**: return quantity ≤ (original sale item quantity - sum of previous returns for that item)

---

### `invoices_invoice`

```sql
id              BIGSERIAL PRIMARY KEY
sale_id         BIGINT UNIQUE NOT NULL REFERENCES sales_sale(id)
invoice_number  VARCHAR(50) NOT NULL         -- same as sale.invoice_number
invoice_html    TEXT                         -- rendered HTML snapshot
print_count     SMALLINT DEFAULT 0
last_printed_at TIMESTAMPTZ
created_at      TIMESTAMPTZ DEFAULT NOW()
```

**Why store invoice_html?** — The rendered invoice should be immune to future template changes. A reprint should look identical to the original. Storing the HTML snapshot guarantees this.

**Indexes**: `sale_id` (UNIQUE), `invoice_number`

---

### `audit_auditlog`

```sql
id          BIGSERIAL PRIMARY KEY
user_id     BIGINT REFERENCES users_user(id) ON DELETE SET NULL
action      VARCHAR(100) NOT NULL
    -- PRODUCT_CREATED, SALE_COMPLETED, STOCK_ADJUSTED, etc.
entity      VARCHAR(100) NOT NULL
    -- 'product', 'sale', 'inventory_transaction', etc.
entity_id   BIGINT
ip_address  INET
metadata    JSONB
created_at  TIMESTAMPTZ DEFAULT NOW()
```

**Indexes**: `user_id`, `action`, `entity + entity_id`, `created_at`

---

### `settings_storesettings`

```sql
id                      BIGSERIAL PRIMARY KEY
store_name              VARCHAR(200) NOT NULL DEFAULT 'Daizzy.online'
store_address           TEXT
phone                   VARCHAR(30)
email                   VARCHAR(254)
website                 VARCHAR(200)
logo                    VARCHAR(500)
currency                VARCHAR(10) DEFAULT 'BDT'
currency_symbol         VARCHAR(5) DEFAULT '৳'
invoice_prefix          VARCHAR(20) DEFAULT 'INV'
invoice_number_format   VARCHAR(100) DEFAULT '{prefix}-{year}-{seq:06d}'
barcode_format          VARCHAR(30) DEFAULT 'CODE128'
default_tax_rate        NUMERIC(5,2) DEFAULT 0
default_discount_rate   NUMERIC(5,2) DEFAULT 0
allow_negative_stock    BOOLEAN DEFAULT FALSE
low_stock_threshold     SMALLINT DEFAULT 5
receipt_width_mm        SMALLINT DEFAULT 80
updated_at              TIMESTAMPTZ DEFAULT NOW()
```

---

## 12. Relationships

```
Category  1 ───── * Product
Product   1 ───── 1 Inventory
Product   1 ───── * InventoryTransaction
Sale      1 ───── * SaleItem
Sale      1 ───── 1 Payment
Sale      1 ───── 1 Invoice
Sale      1 ───── * Return
Return    1 ───── * ReturnItem
SaleItem  1 ───── * ReturnItem
User      1 ───── * Sale (as cashier)
User      1 ───── * InventoryTransaction (as created_by)
User      1 ───── * AuditLog
```

---

## 13. Inventory Ledger Design

### Design Decision: Dual-Write Pattern

The system maintains **both** a denormalized current quantity (`inventory_inventory.quantity`) AND a full transaction ledger (`inventory_inventorytransaction`). These are always updated together in the same atomic transaction.

**Why dual-write instead of recalculating from ledger?**
- `inventory_inventory.quantity` enables O(1) stock lookups during POS operations
- The ledger provides complete audit history
- `select_for_update()` locks the `inventory_inventory` row, preventing race conditions
- Recalculating from ledger would be a costly aggregation query on every scan

### Ledger Transaction Types

| Type | Direction | Trigger |
|------|-----------|---------|
| `OPENING_STOCK` | IN (+) | Manual initial setup |
| `PURCHASE` | IN (+) | Stock addition by inventory manager |
| `SALE` | OUT (-) | Completed sale via POS |
| `RETURN` | IN (+) | Customer return accepted |
| `ADJUSTMENT_IN` | IN (+) | Manual correction upward |
| `ADJUSTMENT_OUT` | OUT (-) | Manual correction downward |
| `DAMAGE` | OUT (-) | Damaged goods removed |
| `LOSS` | OUT (-) | Lost/stolen goods |
| `CORRECTION` | IN or OUT | Administrative correction with reason |

### Example Ledger Trace

```
Product: T-Shirt (SKU: TS-001)

ID   Type           Qty   Dir   Prev  New   Reference
──────────────────────────────────────────────────────
1    OPENING_STOCK   50   +1    0     50    —
2    PURCHASE        20   +1    50    70    —
3    SALE             1   -1    70    69    Sale #INV-2026-000001
4    SALE             2   -1    69    67    Sale #INV-2026-000002
5    DAMAGE           3   -1    67    64    Adjustment #5
6    RETURN           1   +1    64    65    Return #3
```

Reconstructing inventory at any point in time is now possible by replaying ledger entries.

---

## 14. Stock Consistency Strategy

This is the most critical correctness concern in the system.

### The Problem

Two cashiers simultaneously attempt to sell the last 1 unit of a product. Without protection, both reads see `quantity = 1`, both validate `quantity >= 1`, both deduct, and stock becomes `-1`.

### The Solution: Pessimistic Locking

```python
# sales/services.py — SaleService.complete_sale()

from django.db import transaction
from apps.inventory.models import Inventory

def complete_sale(self, cart_data, payment_data, cashier):
    with transaction.atomic():
        
        # Step 1: Acquire row-level locks on ALL inventory rows in this sale
        product_ids = [item['product_id'] for item in cart_data['items']]
        inventories = (
            Inventory.objects
            .select_for_update()           # ← PostgreSQL row-level lock
            .filter(product_id__in=product_ids)
            .order_by('product_id')        # ← consistent ordering prevents deadlock
        )
        inv_map = {inv.product_id: inv for inv in inventories}
        
        # Step 2: Validate stock AFTER acquiring locks
        for item in cart_data['items']:
            inv = inv_map[item['product_id']]
            if inv.quantity < item['quantity']:
                raise InsufficientStockError(item['product_id'], inv.quantity)
        
        # Step 3: Create Sale
        sale = Sale.objects.create(...)
        
        # Step 4: Create SaleItems + deduct inventory
        for item in cart_data['items']:
            SaleItem.objects.create(sale=sale, ...)
            inv = inv_map[item['product_id']]
            prev_qty = inv.quantity
            inv.quantity -= item['quantity']
            inv.save()
            InventoryTransaction.objects.create(
                product_id=item['product_id'],
                transaction_type='SALE',
                quantity=item['quantity'],
                direction=-1,
                previous_quantity=prev_qty,
                new_quantity=inv.quantity,
                reference_type='sale',
                reference_id=sale.id,
                created_by=cashier,
            )
        
        # Step 5: Create Payment
        Payment.objects.create(sale=sale, ...)
        
        # Step 6: Generate Invoice (atomic invoice number)
        invoice_number = InvoiceService.generate_invoice_number()
        Invoice.objects.create(sale=sale, invoice_number=invoice_number, ...)
        
        # All operations committed together on context exit
        return sale
```

### Why `order_by('product_id')` on lock acquisition?

Prevents deadlock when two transactions try to lock the same rows in opposite order. Always acquiring locks in a consistent order guarantees no circular wait.

### Idempotency Protection

To prevent duplicate sale submission (double-click, network retry):

- Generate a **client-side idempotency key** (UUID) when the cashier initiates a sale
- The frontend sends this key in the POST request header: `X-Idempotency-Key`
- The backend checks if a sale with this key was already completed → returns existing sale
- The idempotency key is stored on the Sale record for 24 hours

```sql
-- Add to sales_sale
idempotency_key  UUID UNIQUE
```

---

## 15. Barcode Architecture

### Barcode as First-Class Identity

The barcode is unique at the **database level** (UNIQUE constraint on `products_product.barcode`). Application-level uniqueness checks alone are insufficient due to race conditions.

### Barcode Generation Strategy

```python
# barcode/generators.py

class BarcodeGeneratorStrategy(ABC):
    @abstractmethod
    def generate(self, product: Product) -> str: ...
    
    @abstractmethod
    def validate_format(self, value: str) -> bool: ...

class InternalSequenceGenerator(BarcodeGeneratorStrategy):
    """
    Generates: DZY-000000001
    Uses atomic DB sequence. Safe for concurrent generation.
    """
    def generate(self, product: Product) -> str:
        seq = self._next_sequence()
        return f"DZY-{seq:09d}"

class Code128Generator(BarcodeGeneratorStrategy):
    """
    Generates a valid Code128-compatible string.
    Format: configurable prefix + timestamp + random suffix.
    """

class EAN13Generator(BarcodeGeneratorStrategy):
    """
    Generates a valid EAN-13 barcode with checksum.
    Requires a GS1 company prefix.
    """
```

The active generator is selected from `StoreSettings.barcode_format`. This means switching to EAN-13 later requires changing one setting, not rewriting code.

### Barcode Image Generation

Uses the Python `python-barcode` or `barcode` library to render SVG/PNG barcode images. These can be embedded in printable label templates.

### Barcode Label Template

```
┌──────────────────────────┐
│    DAIZZY.ONLINE          │
│                           │
│  ▌▌▌ ▌▌▌▌▌▌ ▌▌▌▌ ▌▌▌▌▌  │  ← barcode image
│                           │
│  DZY-000000001            │  ← barcode value
│  T-Shirt Large White      │  ← product name
│  SKU: TS-LW-001           │  ← SKU
│  ৳ 450                    │  ← price
└──────────────────────────┘
```

---

## 16. Hardware Scanner Workflow

USB/Bluetooth barcode scanners emulate keyboard input. No driver needed.

```
Physical Scan
     ↓
Scanner sends keystrokes rapidly
     ↓
POS page has a dedicated barcode input field
(always focused, or auto-refocused after each scan)
     ↓
Input receives barcode value + Enter (most scanners append Enter)
     ↓
JavaScript intercepts Enter keypress on barcode field
     ↓
AJAX GET /api/v1/products/barcode/{barcode}/
     ↓
Product found → added to cart (or quantity incremented if already in cart)
     ↓
Barcode field cleared and focused for next scan
     ↓
Audible/visual feedback
```

**Implementation notes**:
- The barcode input field has `autofocus` and is re-focused after every successful scan
- Use `inputmode="none"` on the barcode field to suppress mobile keyboard but allow scanner input
- Detect scanner-speed input (time between first and last character < 100ms) to distinguish scanner from manual typing
- Scanner scans that produce the same barcode twice within 1500ms are treated as duplicate scans and ignored (configurable)

---

## 17. Camera Scanner Workflow

Uses [ZXing-js](https://github.com/zxing-js/library) or [QuaggaJS](https://github.com/serratus/quaggaJS) or the newer **Barcode Detection API** (Chrome/Edge) with ZXing fallback for broader browser support.

**Recommended**: `@zxing/browser` library — supports Code128, EAN-13, QR, and others with good mobile performance.

```
User clicks "📷 Camera" button (or presses F4)
     ↓
CameraScannerModal opens
     ↓
Camera permission requested gracefully
     ↓
Video stream displayed in modal
     ↓
ZXing continuously decodes frames
     ↓
Barcode detected
     ↓
Modal closes automatically
     ↓
Barcode value passed to POS cart logic
     ↓
AJAX lookup and cart update
```

**Error handling**:
- `NotAllowedError` → "Camera permission denied. Please allow camera access."
- `NotFoundError` → "No camera found on this device."
- `NotSupportedError` → "Camera not supported in this browser."
- Invalid barcode detected → show temporary error, keep scanning
- Duplicate scan within 1500ms → silently ignore

---

## 18. POS Workflow

### POS Screen Layout

```
┌────────────────────────────────────────────────────────────────────┐
│  🛒 Daizzy POS    │  Cashier: Sarah  │  📅 17 Sep 2026  │ 14:23  │
├────────────────────────────────────────────────────────────────────┤
│  [🔍 Scan or type barcode / product name ____________] [📷 F4]    │
├─────────────────────────────────────┬──────────────────────────────┤
│  CART                               │  PRODUCT                     │
│                                     │                              │
│  # Product       Qty  Price  Total  │  [Product Image]             │
│  ─────────────────────────────────  │                              │
│  1 T-Shirt Lg    2    450    900    │  T-Shirt Large White         │
│    [−][+] [🗑]                       │  SKU: TS-LW-001              │
│  2 Cap Blue      1    150    150    │  Barcode: DZY-000000042      │
│    [−][+] [🗑]                       │  Price: ৳450.00             │
│                                     │  Stock: 67 pcs               │
│                                     │                              │
├─────────────────────────────────────┴──────────────────────────────┤
│  Items: 3  │  Subtotal: ৳1,050  │  Discount: ৳0  │  Total: ৳1,050 │
│                                                                     │
│  [CLEAR CART]        [💳 F8 PAYMENT]        [✅ F9 COMPLETE SALE]  │
└────────────────────────────────────────────────────────────────────┘
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F2` | Focus barcode/search input |
| `F4` | Open camera scanner |
| `F8` | Open payment panel |
| `F9` | Complete sale (if payment entered) |
| `Esc` | Close modal / cancel action |
| `+` | Increment quantity of last item |
| `-` | Decrement quantity of last item |
| `Delete` | Remove last cart item |
| `Ctrl+Z` | Undo last scan (remove last added item) |

---

## 19. Sales Workflow

### Complete Sale Creation (Transactional)

```
1. Cashier builds cart (scan/search products)
   ↓
2. System validates stock availability (non-locking pre-check for UX)
   ↓
3. Cashier presses F8 → Payment panel opens
   Cashier selects: Cash / bKash / Card / etc.
   Cashier enters amount paid
   System shows change amount
   ↓
4. Cashier presses F9 → Sale submitted
   Frontend generates idempotency key (UUID)
   POST /api/v1/sales/ with idempotency key
   ↓
5. Backend: transaction.atomic() begins
   ↓
6. Check idempotency key → no duplicate
   ↓
7. Acquire inventory row locks: select_for_update()
   (ordered by product_id to prevent deadlock)
   ↓
8. Re-validate stock against locked rows
   If insufficient: rollback + error to frontend
   ↓
9. Create Sale record
   ↓
10. Create SaleItem records (snapshot prices)
    ↓
11. Deduct Inventory.quantity for each product
    ↓
12. Create InventoryTransaction (SALE, direction=-1) for each product
    ↓
13. Create Payment record
    ↓
14. Generate atomic invoice number (see Section 21)
    ↓
15. Render invoice HTML snapshot
    ↓
16. Create Invoice record
    ↓
17. transaction.atomic() commits
    ↓
18. AuditLog entry created (post-commit signal)
    ↓
19. Response: Sale ID, Invoice ID, Invoice Number
    ↓
20. Frontend shows success screen
    ↓
21. Browser opens print dialog for invoice
    (or user presses "Print" button)
    ↓
22. Barcode input re-focused for next sale
```

---

## 20. Return Workflow

```
1. Staff searches for Invoice by number or date
   ↓
2. Invoice opened → sale items displayed
   ↓
3. Staff selects items to return + quantities
   System validates:
   - return quantity ≤ (sold quantity - previously returned quantity)
   - sale status allows returns
   ↓
4. Staff selects refund method + notes
   ↓
5. Submit return → transaction.atomic() begins
   ↓
6. Acquire inventory row locks for returned products
   ↓
7. Create Return record
   ↓
8. Create ReturnItem records
   ↓
9. Restore Inventory.quantity for each returned product
   ↓
10. Create InventoryTransaction (RETURN, direction=+1) for each item
    ↓
11. Update Sale.status:
    - All items returned → RETURNED
    - Partial → PARTIALLY_RETURNED
    ↓
12. transaction.atomic() commits
    ↓
13. AuditLog entry
    ↓
14. Confirmation displayed, optional return receipt printed
```

---

## 21. Invoice Workflow

### Invoice Number Generation (Concurrency-Safe)

```sql
-- PostgreSQL sequence (atomic, no collision possible)
CREATE SEQUENCE invoice_number_seq START 1;

-- In Django migration:
-- operations = [migrations.RunSQL("CREATE SEQUENCE invoice_number_seq START 1;")]
```

```python
# invoices/numbering.py
from django.db import connection
from apps.settings_app.models import StoreSettings

def generate_invoice_number() -> str:
    settings = StoreSettings.get_settings()
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('invoice_number_seq')")
        seq = cursor.fetchone()[0]
    year = timezone.now().year
    return f"{settings.invoice_prefix}-{year}-{seq:06d}"
    # → INV-2026-000001
```

Using a PostgreSQL sequence guarantees no two invoices get the same number, even under concurrent sales. The sequence is also never rolled back (unlike the enclosing transaction), ensuring no gaps cause re-use.

### Invoice HTML Snapshot

After sale completion, the invoice is rendered to HTML using Django's template engine and stored in `invoice.invoice_html`. This means:
- Reprints are pixel-identical to originals
- Template changes don't break historical invoices
- No re-querying of product data for reprints

---

## 22. Printing Architecture

### Phase 1 (MVP): Browser Printing with CSS

All invoices use a dedicated print template with `@media print` CSS:

```css
@media print {
    .no-print { display: none !important; }
    body { font-family: monospace; font-size: 10pt; }
    .invoice-container { width: 80mm; }  /* or 58mm */
}
```

The invoice print page is a standalone HTML page (no sidebar, no navbar) accessible at `/invoices/{id}/print/`.

### Phase 2 (Future): ESC/POS Direct Printing

The architecture leaves space for a `PrinterAdapter` interface:

```python
class PrinterAdapter(ABC):
    def print_invoice(self, invoice: Invoice) -> bool: ...

class BrowserPrintAdapter(PrinterAdapter): ...
class ESCPOSAdapter(PrinterAdapter): ...       # Future
class NetworkPrinterAdapter(PrinterAdapter):  # Future
```

A future implementation could use [python-escpos](https://github.com/python-escpos/python-escpos) for USB/network thermal printers.

---

## 23. REST API Architecture

### Versioning Strategy

URL-based versioning: `/api/v1/`. Headers-based versioning is harder to test and cache. URL versioning is explicit and simple.

### Authentication for API

**JWT (JSON Web Tokens)** via `djangorestframework-simplejwt`:

- POST `/api/v1/auth/token/` → returns `access` + `refresh` tokens
- POST `/api/v1/auth/token/refresh/` → refresh access token
- Access tokens expire in 60 minutes
- Refresh tokens expire in 7 days

**Why JWT over Session auth for API?**
- Session auth requires cookies → CSRF complications for external sites
- JWT is stateless → easy for Daizzy.online website to consume
- JWT works naturally for mobile apps and external systems

**Internal web management** still uses Django session authentication (form login). This is appropriate because the browser automatically handles CSRF cookies.

### API Design Principles

- Consistent response envelope: `{"success": true, "data": {}, "meta": {}}`
- Standard HTTP status codes
- Cursor or page-based pagination
- Field-level filtering via query params
- Ordering via `?ordering=-created_at`
- Search via `?search=keyword`

---

## 24. API Endpoint Specification

### Authentication

```
POST   /api/v1/auth/token/              Login, get JWT tokens
POST   /api/v1/auth/token/refresh/      Refresh access token
POST   /api/v1/auth/logout/             Blacklist refresh token
```

### Products

```
GET    /api/v1/products/                List products (paginated, filterable)
POST   /api/v1/products/                Create product [ADMIN+]
GET    /api/v1/products/{id}/           Get product detail
PATCH  /api/v1/products/{id}/           Update product [ADMIN+]
DELETE /api/v1/products/{id}/           Deactivate product [ADMIN+] (soft delete)

GET    /api/v1/products/barcode/{barcode}/  Lookup by barcode (POS critical path)
GET    /api/v1/products/sku/{sku}/          Lookup by SKU

GET    /api/v1/products/{id}/history/       Inventory transaction history
GET    /api/v1/products/{id}/sales/         Sales history for product
```

### Categories

```
GET    /api/v1/categories/              List categories
POST   /api/v1/categories/              Create category [ADMIN+]
GET    /api/v1/categories/{id}/         Get category detail
PATCH  /api/v1/categories/{id}/         Update category [ADMIN+]
```

### Inventory

```
GET    /api/v1/inventory/               Stock overview (all products with quantities)
GET    /api/v1/inventory/low-stock/     Products below minimum stock level
GET    /api/v1/inventory/out-of-stock/  Products with zero stock

GET    /api/v1/inventory/transactions/              All ledger entries
GET    /api/v1/inventory/transactions/{id}/         Single ledger entry
POST   /api/v1/inventory/adjust/                    Create stock adjustment [INV_MGR+]
```

### Sales

```
GET    /api/v1/sales/                   List sales (paginated)
POST   /api/v1/sales/                   Create sale (POS checkout) [CASHIER+]
GET    /api/v1/sales/{id}/              Get sale detail
POST   /api/v1/sales/{id}/cancel/       Cancel sale [MANAGER+]
```

### Returns

```
GET    /api/v1/returns/                 List returns
POST   /api/v1/returns/                 Create return [CASHIER+]
GET    /api/v1/returns/{id}/            Return detail
```

### Invoices

```
GET    /api/v1/invoices/                List invoices
GET    /api/v1/invoices/{id}/           Invoice detail
GET    /api/v1/invoices/{id}/print/     Print-ready invoice HTML
POST   /api/v1/invoices/{id}/reprint/   Record reprint event [STAFF+]
GET    /api/v1/invoices/number/{number}/  Lookup by invoice number
```

### Barcodes

```
GET    /api/v1/barcodes/lookup/{barcode}/   Quick barcode lookup (public-ish)
POST   /api/v1/barcodes/generate/           Generate barcode for product [INV_MGR+]
POST   /api/v1/barcodes/batch-generate/     Batch generate [INV_MGR+]
GET    /api/v1/barcodes/image/{barcode}/    Barcode image (SVG/PNG)
```

### Reports

```
GET    /api/v1/reports/sales/daily/     Daily sales summary
GET    /api/v1/reports/sales/monthly/   Monthly sales summary
GET    /api/v1/reports/inventory/       Inventory status report
GET    /api/v1/reports/products/top/    Top selling products
```

### Standard Response Envelope

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Requested quantity (5) exceeds available stock (2) for T-Shirt Large White.",
    "details": {
      "product_id": 42,
      "requested": 5,
      "available": 2
    }
  }
}
```

### Standard Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `AUTHENTICATION_REQUIRED` | 401 | Not authenticated |
| `PERMISSION_DENIED` | 403 | Authenticated but not authorized |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Request data invalid |
| `INSUFFICIENT_STOCK` | 409 | Not enough stock for sale |
| `DUPLICATE_BARCODE` | 409 | Barcode already in use |
| `DUPLICATE_SUBMISSION` | 409 | Idempotency key already used |
| `SALE_NOT_CANCELLABLE` | 409 | Sale status prevents cancellation |
| `RETURN_QUANTITY_EXCEEDED` | 409 | Cannot return more than sold |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error (details in logs) |

---

## 25. Authentication / Authorization

### Web Management (Session-based)

- Django `LoginView` with `django.contrib.auth`
- Session cookie (HttpOnly, Secure in production)
- CSRF token on all POST forms
- Login required decorator on all management views
- Role checked via custom `RoleRequiredMixin`

### REST API (JWT-based)

- `djangorestframework-simplejwt`
- Access token: 60 minutes
- Refresh token: 7 days, rotated on use
- Token blacklisting enabled (for logout)

### Permission Classes

```python
# core/permissions.py

class IsAdminOrAbove(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ['SUPER_ADMIN', 'ADMIN']

class IsManagerOrAbove(BasePermission): ...
class IsInventoryManagerOrAbove(BasePermission): ...
class IsCashierOrAbove(BasePermission): ...
class IsReadOnly(BasePermission): ...
```

Each API view specifies its `permission_classes` explicitly.

### External API Authentication

External websites (Daizzy.online frontend) use:
1. A dedicated API user account with `STAFF` role
2. Limited to read-only endpoints
3. Rate-limited separately from internal users
4. CORS allowed for Daizzy.online domain only (configurable)

---

## 26. Security Architecture

| Threat | Mitigation |
|--------|-----------|
| CSRF | Django CSRF middleware on all forms |
| XSS | Django template auto-escaping; CSP header |
| SQL Injection | Django ORM (parameterized queries) |
| Session hijacking | Secure + HttpOnly cookies; session rotation on login |
| Password attacks | bcrypt via Django's password hasher; account lockout |
| File upload attacks | Validate MIME type (not just extension); size limits; store outside webroot |
| API abuse | Rate limiting per user/IP (`django-ratelimit`) |
| Secrets exposure | All secrets in `.env`; never in source code |
| Debug mode | `DEBUG=False` enforced in production settings |
| Directory traversal | Django's `FileField` sanitization |
| Unauthorized access | Server-side role checks on every view and API endpoint |
| Audit trail | All critical actions logged with user + timestamp |
| Double submission | Idempotency keys on sale creation |

### CORS Policy

```python
# config/settings/production.py
CORS_ALLOWED_ORIGINS = [
    "https://daizzy.online",
    "https://www.daizzy.online",
]
CORS_ALLOW_CREDENTIALS = False   # JWT is in Authorization header, not cookies
```

---

## 27. Audit Logging

### Events Logged

| Event | Severity |
|-------|----------|
| `USER_LOGIN` | INFO |
| `USER_LOGOUT` | INFO |
| `USER_LOGIN_FAILED` | WARNING |
| `PRODUCT_CREATED` | INFO |
| `PRODUCT_UPDATED` | INFO |
| `PRODUCT_DEACTIVATED` | WARNING |
| `BARCODE_CHANGED` | WARNING |
| `STOCK_ADJUSTED` | WARNING |
| `SALE_COMPLETED` | INFO |
| `SALE_CANCELLED` | WARNING |
| `RETURN_CREATED` | INFO |
| `INVOICE_REPRINTED` | INFO |
| `USER_PERMISSION_CHANGED` | WARNING |
| `API_RATE_LIMIT_EXCEEDED` | WARNING |

### AuditService Usage

```python
# Example: audit sale completion
AuditService.log(
    user=request.user,
    action='SALE_COMPLETED',
    entity='sale',
    entity_id=sale.id,
    metadata={
        'invoice_number': sale.invoice_number,
        'grand_total': str(sale.grand_total),
        'item_count': sale.items.count(),
    },
    ip_address=request.META.get('REMOTE_ADDR'),
)
```

Audit logs are **never deleted**. They may be archived to cold storage after a retention period.

---

## 28. Frontend Architecture

### Technology Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| HTML | Django Templates | Server-rendered, fast, SEO-ready |
| CSS | Vanilla CSS with CSS custom properties | Full control, no framework lock-in |
| JS | Vanilla JS + small focused libraries | No build step needed for MVP |
| Barcode scanning | @zxing/browser (CDN) | Best mobile/desktop camera support |
| Charts | Chart.js (CDN, dashboard only) | Lightweight, good looking |
| Icons | Phosphor Icons (CDN) | Clean, consistent icon set |
| Fonts | Inter (Google Fonts) | Professional, highly readable |
| Print | CSS @media print | No special software needed |

**Why not React/Vue?** For a business management system primarily accessed on company devices, server-rendered Django templates with targeted JS are faster to develop, easier to maintain, and avoid the complexity of a separate SPA build pipeline. The POS screen does use richer client-side JavaScript but doesn't warrant a full SPA framework.

### Template Structure

```
templates/
├── base/
│   ├── base.html          ← Sidebar + topbar + content area
│   ├── base_auth.html     ← Login page (no sidebar)
│   └── base_print.html    ← Print-only, minimal chrome
├── components/
│   ├── sidebar.html
│   ├── topbar.html
│   ├── data_table.html    ← Reusable table with pagination
│   ├── stock_badge.html   ← In stock / Low / Out of stock badge
│   ├── status_badge.html  ← Sale status badge
│   └── toast.html         ← Notification toast
├── dashboard/
│   └── index.html
├── products/
│   ├── list.html
│   ├── detail.html
│   ├── create.html
│   └── edit.html
├── pos/
│   └── pos.html           ← Full-screen POS interface
├── invoices/
│   ├── list.html
│   ├── detail.html
│   └── print.html         ← Print-ready invoice
└── ...
```

---

## 29. UI/UX Design System

### Color Palette

```css
:root {
    /* Brand */
    --color-primary: hsl(220, 90%, 56%);        /* Vibrant blue */
    --color-primary-dark: hsl(220, 90%, 45%);
    --color-primary-light: hsl(220, 90%, 92%);
    
    /* Semantic */
    --color-success: hsl(145, 65%, 42%);
    --color-warning: hsl(38, 92%, 50%);
    --color-danger: hsl(0, 78%, 55%);
    --color-info: hsl(200, 80%, 50%);
    
    /* Neutrals (dark mode inspired) */
    --color-bg: hsl(220, 20%, 97%);
    --color-surface: hsl(0, 0%, 100%);
    --color-surface-2: hsl(220, 20%, 95%);
    --color-border: hsl(220, 15%, 88%);
    --color-text: hsl(220, 25%, 15%);
    --color-text-muted: hsl(220, 15%, 50%);
    
    /* POS specific */
    --color-pos-bg: hsl(220, 25%, 13%);
    --color-pos-surface: hsl(220, 22%, 18%);
    --color-pos-accent: hsl(220, 90%, 56%);
    
    /* Typography */
    --font-sans: 'Inter', -apple-system, sans-serif;
    --font-mono: 'JetBrains Mono', 'Courier New', monospace;
    
    /* Spacing scale */
    --space-1: 4px;  --space-2: 8px;  --space-3: 12px;
    --space-4: 16px; --space-6: 24px; --space-8: 32px;
    
    /* Border radius */
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 16px;
    
    /* Shadows */
    --shadow-sm: 0 1px 3px hsla(220,25%,15%,0.08);
    --shadow-md: 0 4px 16px hsla(220,25%,15%,0.12);
}
```

### The POS screen uses a **dark theme** — this is intentional. POS terminals are often in bright retail environments; a dark background reduces eye strain during long shifts.

### Typography Scale

| Role | Size | Weight |
|------|------|--------|
| Page title | 24px | 700 |
| Section heading | 18px | 600 |
| Body | 14px | 400 |
| Small/label | 12px | 500 |
| Monospace (SKU/barcode) | 13px | 400 |

---

## 30. Page-by-Page UI Specification

### Dashboard

- 4 stat cards: Total Products, Today's Revenue, Today's Orders, Low Stock Count
- Recent Sales table (last 10)
- Low Stock alerts list
- Quick actions: [Go to POS], [Add Product], [Stock Adjustment]

### Product List (`/products/`)

- Search bar + Category filter + Status filter
- Sortable table: Name, SKU, Barcode, Category, Price, Stock, Status, Actions
- Inline stock badge (green/yellow/red)
- Bulk action: Generate/Print barcodes

### Product Detail (`/products/{id}/`)

- Full product info card with image
- Inventory history table (ledger entries)
- Sales history table
- Barcode display with print button
- Edit button (role-checked)

### POS Screen (`/pos/`)

- Dark theme, full viewport
- Barcode input prominently at top
- Cart on left, product info panel on right
- Payment panel slides in from right on F8
- Keyboard shortcut legend visible at bottom

### Sales History (`/sales/`)

- Date range filter + cashier filter + status filter
- Table: Invoice#, Date, Cashier, Items, Total, Status, Actions
- Click row to view detail
- Export to CSV (future)

### Invoice Print (`/invoices/{id}/print/`)

- Minimal print layout, no navigation
- Auto-opens print dialog on load (configurable)
- "Print" button for manual reprint

### Stock Adjustment (`/inventory/adjust/`)

- Product search/select
- Current stock display
- Adjustment type selector
- Quantity input
- New stock preview (live calculation)
- Reason (required) + Notes
- Submit with confirmation dialog

### Barcode Management (`/barcode/`)

- Product list with barcode column
- Filter products without barcode
- Generate barcode for selected products
- Preview label before print
- Batch print labels

---

## 31. Component Architecture

### Reusable JS Components

```javascript
// static/js/pos.js
class POSCart {
    addItem(product) { ... }
    removeItem(productId) { ... }
    updateQuantity(productId, qty) { ... }
    applyDiscount(type, value) { ... }
    calculateTotals() { ... }
    clear() { ... }
    serialize() { ... }     // For sale submission
}

class BarcodeInput {
    constructor(inputEl, onScan) { ... }
    focus() { ... }
    detectScannerInput(value, timeMs) { ... }
    handleScan(barcode) { ... }
}

class ToastNotification {
    success(message, duration = 3000) { ... }
    error(message, duration = 5000) { ... }
    warning(message, duration = 4000) { ... }
}
```

---

## 32. Error Handling

### Backend

- Custom exception classes in `core/exceptions.py`
- DRF exception handler returns consistent JSON envelope
- Django views use try/except and display user-friendly error messages
- All unhandled exceptions logged to application log

### Frontend

- AJAX errors caught and displayed via `ToastNotification`
- Stock errors show inline warning in cart
- Network errors show retry prompt
- Form validation errors displayed below each field

---

## 33. Validation Rules

| Rule | Layer |
|------|-------|
| Barcode uniqueness | DB UNIQUE + Service check |
| SKU uniqueness | DB UNIQUE + Service check |
| Quantity > 0 | DB CHECK + Serializer |
| Price ≥ 0 | DB CHECK + Serializer |
| Stock not negative | Service layer + DB CHECK |
| Return qty ≤ sold qty | Service layer |
| Invoice number unique | DB UNIQUE + Sequence |
| Image file type | Service layer (MIME check) |
| Image size limit | Service layer (configurable) |
| Role has permission | Permission class + decorator |
| Sale not double-submitted | Idempotency key check |

---

## 34. Reporting

### MVP Reports

#### Sales Dashboard
- Today's revenue, order count, average order value
- Revenue by payment method (pie chart)
- Hourly sales trend (bar chart, today)
- Daily sales for last 30 days (line chart)

#### Inventory Report
- Current stock value (sum of cost_price × quantity)
- Products count by status
- Low stock list (downloadable)
- Top 10 most moved products (last 30 days)

#### Product Report
- Top selling products by quantity
- Top selling products by revenue
- Products with zero sales (last 30 days)

All reports are generated by `ReportService` using aggregated Django ORM queries. No raw SQL unless necessary for performance.

---

## 35. Performance

### Query Optimization

- `select_related()` on ForeignKey traversals (Sale → cashier, SaleItem → product)
- `prefetch_related()` on reverse relations (Sale → SaleItem set)
- `only()` / `defer()` to fetch only needed fields in list views
- Database indexes on all filter/order/search fields

### Pagination

- Default page size: 20
- Maximum page size: 100
- Cursor pagination for very large datasets (inventory transactions)

### Caching

- Dashboard aggregate stats: cached for 5 minutes in database (simple cache table, no Redis needed for MVP)
- Store settings: cached in memory per request (via Django's per-request caching)

### Future Async Processing

If the system grows, these operations can move to Celery:
- Barcode image generation (batch)
- Report generation (large date ranges)
- Email sending (invoice to customer)
- Daily low-stock notification

No Celery in MVP. Identified clearly as a future path.

---

## 36. Testing Strategy

### Unit Tests

```python
# tests/test_barcode.py
def test_barcode_uniqueness_enforced(): ...
def test_barcode_generator_produces_valid_format(): ...
def test_ean13_checksum_calculation(): ...

# tests/test_sales.py
def test_sale_deducts_inventory(): ...
def test_sale_fails_on_insufficient_stock(): ...
def test_discount_calculation_correct(): ...
def test_line_total_calculation(): ...
def test_change_amount_calculation(): ...

# tests/test_inventory.py
def test_stock_adjustment_creates_ledger_entry(): ...
def test_ledger_previous_and_new_quantity_correct(): ...
def test_return_restores_stock(): ...
```

### Integration Tests

```python
# tests/test_integration_sale.py
def test_complete_sale_workflow():
    # Create product, set stock, run sale via API, check inventory deducted,
    # check invoice created, check ledger entry created
    ...

def test_sale_rollback_on_insufficient_stock():
    # Ensure no partial writes if stock check fails mid-transaction
    ...
```

### Concurrency Test

```python
# tests/test_concurrency.py
import threading

def test_simultaneous_sale_of_last_item():
    """
    Two threads simultaneously attempt to sell the last 1 unit.
    Only one should succeed; the other should get InsufficientStockError.
    Final inventory must be 0, not -1.
    """
    product = create_product_with_stock(1)
    results = []
    
    def sell():
        try:
            SaleService.complete_sale(...)
            results.append('success')
        except InsufficientStockError:
            results.append('error')
    
    t1 = threading.Thread(target=sell)
    t2 = threading.Thread(target=sell)
    t1.start(); t2.start()
    t1.join(); t2.join()
    
    assert results.count('success') == 1
    assert results.count('error') == 1
    assert Inventory.objects.get(product=product).quantity == 0
```

### API Tests

- Every endpoint tested with correct auth, wrong auth, and no auth
- Pagination, filtering, ordering tested
- Error responses tested for correct format

---

## 37. Deployment Architecture

```
Internet
   │ HTTPS (TLS 1.3)
   ▼
Nginx                          ← Reverse proxy, static/media files
   │
   ▼
Gunicorn (4-8 workers)         ← Django WSGI server
   │
   ▼
Django Application
   │
   ├──► PostgreSQL 16           ← Primary database
   │
   └──► /media/                 ← Uploaded product images
        (local or S3-compatible)
```

### Environment Variables (`.env`)

```env
SECRET_KEY=...
DEBUG=False
DATABASE_URL=postgresql://user:pass@localhost:5432/daizzy_ims
ALLOWED_HOSTS=ims.daizzy.online
MEDIA_ROOT=/var/www/daizzy_ims/media
STATIC_ROOT=/var/www/daizzy_ims/static
CORS_ALLOWED_ORIGINS=https://daizzy.online
```

### Production Checklist

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` from environment, not source code
- [ ] HTTPS enforced (HSTS header)
- [ ] Static files served by Nginx
- [ ] Media files served by Nginx
- [ ] PostgreSQL with password authentication
- [ ] Gunicorn behind Nginx
- [ ] Systemd service for Gunicorn
- [ ] Log rotation configured
- [ ] Firewall: only 80/443 open publicly, 5432 localhost only
- [ ] Automated database backups

---

## 38. Backup Strategy

### Database Backups

```bash
# Daily automated backup via cron
pg_dump -Fc daizzy_ims > /backups/db/daizzy_ims_$(date +%Y%m%d).dump

# Retention: 7 daily, 4 weekly, 12 monthly
```

### Media Backups

Product images are uploaded to `/media/`. These must be backed up alongside the database.

### Critical Data Priority

| Data | Criticality | Backup Frequency |
|------|-------------|-----------------|
| Sales records | 🔴 Critical | Hourly WAL archiving |
| Inventory ledger | 🔴 Critical | Hourly WAL archiving |
| Products/Barcodes | 🔴 Critical | Daily |
| Invoice HTML snapshots | 🔴 Critical | Daily |
| Product images | 🟠 High | Daily |
| Audit logs | 🟠 High | Daily |
| Report data | 🟡 Medium | Daily (derived from above) |

### Restore Procedure

1. Restore PostgreSQL dump: `pg_restore -d daizzy_ims backup.dump`
2. Restore media directory from backup
3. Run `python manage.py migrate` to verify schema
4. Verify with smoke test: login, view products, view invoices

---

## 39. Development Roadmap

### Phase 1 — Foundation (Week 1-2)
- Django project setup with modular settings
- PostgreSQL configuration
- Custom User model with roles
- Core app (TimeStampedModel, permissions, exceptions)
- Base UI template (sidebar, topbar, design system CSS)
- Django admin registration for core models

### Phase 2 — Product Catalog (Week 3)
- Category model + CRUD
- Product model + CRUD
- Product image upload with validation
- Product search and filtering
- SKU auto-generation
- Product list/detail pages

### Phase 3 — Inventory (Week 4)
- Inventory model (linked to Product)
- InventoryTransaction ledger
- Stock adjustment workflow
- InventoryService + StockAdjustmentService
- Low stock detection
- Inventory history page

### Phase 4 — Barcode (Week 5)
- BarcodeService with strategy pattern
- Barcode generation (internal sequence)
- Barcode image generation
- Barcode label template
- Batch label printing page
- Barcode search/lookup API

### Phase 5 — POS (Week 6-7)
- POS screen template (dark theme)
- Cart JavaScript (POSCart class)
- Hardware scanner input handling
- Camera scanner integration (ZXing)
- Payment panel
- Sale creation API endpoint
- `select_for_update()` locking in SaleService
- Idempotency key handling
- Success screen

### Phase 6 — Invoice (Week 8)
- Invoice model
- Invoice number generation (PostgreSQL sequence)
- Invoice HTML rendering and snapshot storage
- Invoice print template (80mm/58mm)
- Invoice list and detail pages
- Reprint functionality

### Phase 7 — Returns (Week 9)
- Return and ReturnItem models
- ReturnService with inventory restoration
- Return creation workflow
- Return from invoice page
- Return confirmation and receipt

### Phase 8 — REST API (Week 10)
- DRF setup and JWT authentication
- Product, Category, Inventory API endpoints
- Sales and Returns API endpoints
- Invoice API endpoints
- CORS configuration for Daizzy.online
- Rate limiting
- API documentation (DRF Spectacular / Swagger UI)

### Phase 9 — Reports (Week 11)
- ReportService
- Sales dashboard charts
- Inventory report page
- Product performance report
- Export to CSV (basic)

### Phase 10 — Security, Testing, Deployment (Week 12)
- Complete unit test suite
- Integration tests
- Concurrency tests
- Security hardening
- Production settings
- Deployment documentation
- Nginx + Gunicorn configuration

---

## 40. Recommended Project Folder Structure

*(See Section 7 for the detailed tree — this is the authoritative structure)*

Key decisions explained:
- `config/settings/` split into `base.py`, `development.py`, `production.py` — no single settings file to avoid accidental production exposure of debug settings
- `apps/core/` — shared abstractions to prevent duplication
- `apps/api/v1/urls.py` — centralized API routing
- `apps/pos/` — UI-only, delegates to `apps/sales/services.py`
- `requirements/` split — dev tools (debug-toolbar, factory-boy) don't go to production

---

## 41. Recommended Dependencies

### Core

```txt
# requirements/base.txt
Django==5.1.*
djangorestframework==3.15.*
djangorestframework-simplejwt==5.3.*
psycopg2-binary==2.9.*          # PostgreSQL adapter
Pillow==10.*                     # Image processing
python-barcode==0.15.*           # Barcode image generation
qrcode==7.*                      # QR code support (future)
django-filter==24.*              # API filtering
django-cors-headers==4.*         # CORS support
whitenoise==6.*                  # Static files in production
gunicorn==22.*                   # Production WSGI server
python-decouple==3.*             # Environment variable management
```

### Development

```txt
# requirements/development.txt
-r base.txt
django-debug-toolbar==4.*
factory-boy==3.*                 # Test data factories
faker==26.*                      # Fake data generation
pytest-django==4.*
pytest-xdist==3.*                # Parallel test execution
coverage==7.*
drf-spectacular==0.27.*          # OpenAPI/Swagger docs
```

### Production

```txt
# requirements/production.txt
-r base.txt
sentry-sdk==2.*                  # Error tracking
django-ratelimit==4.*            # API rate limiting
```

---

## 42. Future Extension Points

The architecture is designed to accommodate these without core restructuring:

| Feature | Extension Approach |
|---------|-------------------|
| Multi-store / Branch | Add `Store` model; scope all queries to store |
| Offline POS | Service worker + IndexedDB + sync queue |
| ESC/POS printing | `ESCPOSAdapter` implementing `PrinterAdapter` |
| Payment gateways | `PaymentHandlerFactory` extension |
| Customer loyalty | Add `Customer` model with point balance |
| Purchase orders | New `purchasing` app with `PurchaseOrder` model |
| SMS/Email notifications | Celery + notification service |
| Mobile app | REST API already prepared |
| Advanced analytics | Export to data warehouse / connect BI tool |
| Webhook integrations | Observer pattern → webhook dispatch |
| EAN-13 barcodes | `EAN13Generator` strategy (already stubbed) |

---

## 43. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|:-----------:|:------:|-----------|
| Database concurrent sale conflict | Medium | 🔴 Critical | `select_for_update()` + transaction.atomic() |
| Duplicate invoice numbers | Low | 🔴 Critical | PostgreSQL sequence (never rolled back) |
| Stock goes negative | Low | 🔴 Critical | Service-layer check + DB constraint + locking |
| Camera scanner browser compatibility | Medium | 🟠 High | ZXing with graceful fallback + hardware scanner as primary |
| Slow POS barcode lookup | Low | 🟠 High | DB index on barcode column + caching |
| Product image abuse (malicious upload) | Medium | 🟠 High | MIME type validation + size limits + storage outside webroot |
| Session fixation / auth bypass | Low | 🔴 Critical | Session rotation on login; HTTPS; secure cookies |
| Data loss on server failure | Medium | 🔴 Critical | PostgreSQL WAL archiving + daily backups |
| Thermal printer compatibility | Medium | 🟡 Medium | CSS print styles work on all printers; ESC/POS as Phase 2 |
| POS network failure mid-sale | Low | 🟠 High | Idempotency key; clear UI error; retry button |

---

## 44. Final Architecture Summary

### A. Recommended Architecture
**Modular Django Monolith** with PostgreSQL, Django REST Framework, and vanilla JavaScript frontend. Single deployable unit. Clean app separation by domain.

### B. Why This Is Appropriate for Daizzy.online
Daizzy.online needs reliability, speed of development, and maintainability — not distributed system complexity. A well-structured monolith on Django is the industry-proven choice for this scale.

### C. Database Architecture
PostgreSQL with a carefully designed schema:
- Inventory ledger (full audit trail)
- Denormalized current quantity (fast POS lookups)
- Price snapshots in SaleItem (historical accuracy)
- PostgreSQL sequence for invoice numbering (concurrent-safe)
- Row-level locking via `select_for_update()` for sale operations

### D. Django App Architecture
10 focused apps (`core`, `users`, `products`, `inventory`, `barcode`, `sales`, `pos`, `invoices`, `reports`, `audit`) with a service layer in each. Clear separation: views handle HTTP, services handle business logic, models handle persistence.

### E. REST API Architecture
Versioned (`/api/v1/`), JWT-authenticated, consistent response envelope, rate-limited. Ready for Daizzy.online website integration from day one.

### F. POS Architecture
Dark-themed, keyboard-optimized POS screen. Hardware scanner = keyboard input to a focused text field. Camera scanner = ZXing library in a modal. Both paths converge to the same cart logic. `select_for_update()` prevents race conditions on checkout.

### G. Barcode Architecture
Strategy pattern for generation (configurable format). Database UNIQUE constraint enforces one-barcode-one-product invariant. Barcode image generation via python-barcode. Batch label printing via CSS print page.

### H. Printing Architecture
Phase 1: CSS `@media print` with dedicated print templates (works on any printer). Phase 2: ESC/POS adapter (designed but not implemented in MVP).

### I. Security Architecture
Defense in depth: CSRF, session security, JWT for API, server-side RBAC, rate limiting, file upload validation, audit logging, secrets in environment variables.

### J. Frontend/UI Architecture
Django templates + CSS custom properties design system + vanilla JS. POS has a dark theme for operational clarity. All interactive components are reusable. No build step required.

### K. Development Roadmap
10-phase, 12-week development plan. Each phase delivers working, testable functionality. Foundation → Products → Inventory → Barcode → POS → Invoices → Returns → API → Reports → Deploy.

### L. Risks
Primary risk: inventory race conditions under concurrent sales. Mitigated by `select_for_update()`. Secondary risk: camera scanner browser support. Mitigated by hardware scanner as primary path and ZXing's broad compatibility.

### M. Future Scalability Options
- **Scale up**: Larger server; PostgreSQL connection pooling (pgBouncer)
- **Scale out**: Read replicas for reports; Celery for async tasks
- **Architectural evolution**: Extract REST API into separate service if external load demands it; add Redis for caching; add Elasticsearch for full-text product search

---

> [!IMPORTANT]
> **Next Steps After Approval**
> 1. Approve this PDG (or request modifications)
> 2. Confirm technology preferences (especially barcode format and payment methods)
> 3. Confirm the development phase sequence
> 4. Begin **Phase 1** code generation: Django project scaffold, settings, core models, and base UI

---

*Daizzy IMS — Product Development Guide v1.0*  
*Prepared by Antigravity AI · September 2026*
