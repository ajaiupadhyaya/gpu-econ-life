# GPU rental price panel (derived monthly aggregates)

Companion dataset to the working paper "Rental-Implied Depreciation of AI Accelerators: Why the
Estimates Disagree". Built by `gel.release.dataset` from the replication repository.

- `gpu_rental_panel.csv`: one row per listing-month: the median of a month's posted prices for
  one provider, SKU, chip, GPU count, form factor, region, contract type and term, in USD per
  GPU-hour (nominal, and in 2025 dollars using BLS CPI-U). `collector` names the source(s); rows
  available only from the SkyPilot catalog history are omitted because that catalog has no
  licence. They are re-created by the repository's collector.
- `chips.csv`: chip specifications and release dates from Epoch AI, "Data on machine learning
  hardware" (CC BY 4.0), as used in the paper.

Licence: the panel is released under CC BY 4.0 as a compilation of facts (posted prices),
except where a provider's terms say otherwise; see `docs/data_sources.md` in the repository.
Prices are posted list, spot and reserved prices, not transaction prices.
