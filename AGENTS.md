# Blink agent entry rules

Before changing Blink, read these in order:

1. [`docs/contracts/BLINK_PRODUCT_REQUIREMENTS.md`](docs/contracts/BLINK_PRODUCT_REQUIREMENTS.md)
2. [`docs/BLINK_PRODUCT_PHILOSOPHY.md`](docs/BLINK_PRODUCT_PHILOSOPHY.md)
3. [`docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`](docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md)
4. [`docs/implementation/BLINK_REMAINING_ROADMAP.md`](docs/implementation/BLINK_REMAINING_ROADMAP.md)
5. [`docs/BLINK_DESIGN_DOCUMENT.md`](docs/BLINK_DESIGN_DOCUMENT.md)

The first file is the compact product requirements and delivery direction. The
current-state contract defines technical ownership and boundaries; the
roadmap defines verified status. Do not infer product priorities from a single
Shortcut failure or an old historical report.

For Shortcut work, follow the simulator-first sequence in the requirements and
the `shortcuts-simulator-first` skill. Preserve the Mac source of truth, the
one-file CREATE Share Sheet contract, explicit validation, and rollback until
Production acceptance is complete.
