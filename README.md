# Accretion/dilution model: CRH's acquisition of Arcosa

A Python model that answers the first question asked about most acquisitions: **will the deal raise or lower the buyer's earnings per share (EPS)?**

It is applied to CRH's $8.5bn all-cash acquisition of Arcosa, announced on 22 June 2026 and expected to close in Q1 2027. CRH said the deal would be "accretive to earnings ... in the first 12 months post-completion" (before one-off costs). The model checks that claim from public figures and shows how much it depends on the assumptions.

## Results (base case)

| | Synergies (pre-tax, $m) | Pro forma EPS | Accretion |
|---|---|---|---|
| CRH standalone | | $5.91 | |
| Year 1 | 60 | $5.92 | +0.2% |
| Year 2 | 130 | $6.00 | +1.6% |
| Year 3 | 175 | $6.05 | +2.5% |

- **Accretive, but only just in year 1.** The deal needs about **$50m** of pre-tax synergies to break even, against the ~$60m CRH expects in year 1.
- **Why it is tight:** CRH is paying 35x Arcosa's earnings, an earnings yield of 2.8%, while new debt costs about 3.9% after tax. Arcosa's own earnings alone don't cover the interest; the interest saved on Arcosa's repaid debt and the synergies make up the gap.
- **Why cash, not shares:** CRH's own shares trade on about 14x earnings. Paying for Arcosa entirely in new CRH shares would cut year-1 EPS by about 5% (table 2).
- **Price check:** the model gives an enterprise value of $8.4bn, 14.9x Arcosa's 2026 EBITDA before synergies and 11.3x with them, close to CRH's quoted $8.5bn and 11.5x.
- **What could make it dilutive:** a cost of new debt above about 5.15%, or extra amortisation from revaluing Arcosa's assets (tables 1 and 3).

Run `python3 run.py` to see the full output, including the after-tax bridge and all three sensitivity tables.

## How it works

```
Pro forma net income = CRH net income
                     + Arcosa net income
                     + Arcosa's interest cost saved (CRH repays Arcosa's debt)
                     + cost synergies
                     - interest on new debt
                     - interest CRH no longer earns on the cash it spends
                     - extra amortisation from revaluing Arcosa's assets
                     (every adjustment after tax)

Pro forma EPS = pro forma net income / (CRH shares + any new shares issued)
Accretion     = pro forma EPS / CRH standalone EPS - 1
```

It also works out the synergies needed to break even, and three sensitivity tables:

1. Year-1 accretion by cost of new debt and synergies
2. Year-1 accretion by how much of the price is paid in CRH shares, and CRH's share price
3. Year-3 accretion by offer price and extra amortisation

## Inputs and sources

All inputs are in `crh_arcosa.json` (US$ millions), with a source for each.

| Input | Value | Source |
|---|---|---|
| Offer price | $150 per share, all cash | CRH press release, 22 Jun 2026 |
| Synergies | $60m, $130m, $175m (years 1-3) | CRH deal presentation, 22 Jun 2026 |
| CRH net income | $4,000m | CRH 2026 guidance, $3.9-4.1bn (FY2025 results) |
| CRH diluted shares | 677.0m | CRH FY2025 results |
| CRH tax rate | 21.7% | CRH FY2025: tax $1,041m / pre-tax income $4,805m |
| CRH share price | $81.54 | Close on 9 Oct 2026 (only used when paying in shares) |
| Arcosa net income | $209.5m | Arcosa 2026 guidance, $200.4-218.6m (Q1 2026 results) |
| Arcosa diluted shares | 49.2m | Arcosa Q1 2026 results |
| Arcosa net debt | $1,012.8m | Arcosa, 31 Mar 2026, after the barge business sale |
| Arcosa interest expense | $80m | Arcosa 2026 guidance, $79-81m |
| Arcosa adjusted EBITDA | $565m | 2026 guidance midpoint, as used in CRH's presentation |
| Cash used | $1,500m | **Assumption** (CRH had $4.1bn of cash at end-2025 and gave no split) |
| Cost of new debt | 5.0% | **Assumption**: coupon on CRH's 10-year notes issued Oct 2025 |
| Interest earned on cash | 3.5% | **Assumption**: CRH's FY2025 interest income / year-end cash |
| Extra amortisation | $0 | **Assumption**: not disclosed, so tested in table 3 |

## Running it

Needs Python 3.9 or later and no extra packages.

```bash
python3 run.py                       # CRH / Arcosa
python3 run.py --deal my_deal.json   # any other deal: copy crh_arcosa.json and change the numbers
python3 -m unittest discover tests   # tests
```

The summary and the sensitivity tables are also saved to `results/`.

## Limitations

- Both companies' earnings are held at their 2026 guidance for all three years, so only the synergies change from year to year.
- One-off costs (advisory fees, financing fees, integration costs) are left out, as in CRH's own accretion statement.
- All adjustments are taxed at CRH's rate.
- The split between cash and new debt is an assumption; CRH did not publish one.
- It ignores share buybacks, Arcosa's growth and any change in CRH's credit rating or borrowing costs.
