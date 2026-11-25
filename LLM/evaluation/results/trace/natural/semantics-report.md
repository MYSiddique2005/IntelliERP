# Concept checker on the labelled natural-error sentences

DEVELOPMENT result: the patterns were written after reading these sentences (see semantics_eval.py).

| Method | Recall on the 19 false sentences of the random sample | Precision of flags (686 pooled sentences) |
|---|---:|---:|
| TRACE-hybrid (published) | 4/19 (21%) | 12/78 (15%) |
| Concept checker alone | 14/19 (74%) | 30/30 (100%) |
| TRACE-hybrid + concept checker | 17/19 (89%) | 41/107 (38%) |

Concept checker flagged 30 of 686 pooled sentences; 30 labelled; wrong flags: 0.
False sentences it found in the whole pool: 30/55 (55%).
In the random sample of 300 labelled sentences it flagged 14.

## Wrong flags


## False sentences in the random sample the concept checker missed

- The stock status is Low Stock because the 125 units are below the reorder level of 92 plus safety stock rules, but the stockout risk level is Low, with a projected stockout date of 2026-11-20 and no c
- Purchase orders awaiting approval do not count as incoming stock in projections; only orders with approved or ordered status that are on their way are factored into incoming inventory.
- - Inbound units are already on order (which prevents the status from escalating to High or Critical risk).
- - Suggested reorder quantity: 40 units
- The stock status is low stock because current stock is below the reorder level of 92, but it is not out of stock.
