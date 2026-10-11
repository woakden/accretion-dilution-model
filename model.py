"""Accretion/dilution: does buying the target raise or lower the acquirer's earnings per share (EPS)?

Pro forma net income = acquirer net income
                     + target net income
                     + target's interest cost saved, if the acquirer repays the target's debt
                     + cost synergies
                     - interest on new debt raised to pay for the deal
                     - interest the acquirer no longer earns on cash it spends
                     - extra amortisation from revaluing the target's assets
(every adjustment after tax)

Pro forma shares = acquirer shares + new shares issued to the target's shareholders (if any)

Accretion = pro forma EPS / acquirer's standalone EPS - 1. Positive = accretive, negative = dilutive.
All money amounts are in millions; per-share amounts in units of currency.
"""
import json
from dataclasses import dataclass, replace
from pathlib import Path


@dataclass(frozen=True)
class Deal:
    offer_price: float            # paid per target share
    percent_in_shares: float      # 0 = all cash, 1 = all acquirer shares
    synergies: dict               # pre-tax cost synergies by year, e.g. {"Year 1": 60}
    extra_amortisation: float     # pre-tax, per year

    acquirer_net_income: float
    acquirer_shares: float
    acquirer_price: float
    tax_rate: float

    target_net_income: float
    target_shares: float
    target_net_debt: float
    target_interest: float
    target_ebitda: float
    refinance_target_debt: bool

    cash_used: float              # acquirer's own cash put towards the deal; the rest is borrowed
    cost_of_debt: float
    interest_on_cash: float

    acquirer_name: str = "Acquirer"
    target_name: str = "Target"


def load(path):
    """Read a deal from a JSON file like crh_arcosa.json."""
    raw = json.loads(Path(path).read_text())
    d, a, t, f = raw["deal"], raw["acquirer"], raw["target"], raw["financing"]
    return Deal(
        offer_price=d["offer_price_per_share"],
        percent_in_shares=d["percent_paid_in_shares"],
        synergies=d["synergies_pre_tax"],
        extra_amortisation=d.get("extra_amortisation_pre_tax", 0.0),
        acquirer_net_income=a["net_income"],
        acquirer_shares=a["diluted_shares"],
        acquirer_price=a["share_price"],
        tax_rate=a["tax_rate"],
        target_net_income=t["net_income"],
        target_shares=t["diluted_shares"],
        target_net_debt=t["net_debt"],
        target_interest=t["interest_expense"],
        target_ebitda=t.get("adjusted_ebitda", 0.0),
        refinance_target_debt=t.get("refinance_debt", True),
        cash_used=f["cash_used"],
        cost_of_debt=f["cost_of_new_debt"],
        interest_on_cash=f["interest_rate_on_cash"],
        acquirer_name=a.get("name", "Acquirer"),
        target_name=t.get("name", "Target"),
    )


def with_changes(deal, **changes):
    """A copy of the deal with some inputs changed (used for the sensitivity tables)."""
    return replace(deal, **changes)


def standalone_eps(deal):
    return deal.acquirer_net_income / deal.acquirer_shares


def financing(deal):
    """How the purchase is paid for: equity value, cash needed, cash used, new debt and new shares."""
    equity_value = deal.offer_price * deal.target_shares
    paid_in_shares = equity_value * deal.percent_in_shares
    cash_needed = equity_value - paid_in_shares
    if deal.refinance_target_debt:
        cash_needed += deal.target_net_debt
    cash_used = min(deal.cash_used, cash_needed)
    return {
        "equity_value": equity_value,
        "enterprise_value": equity_value + deal.target_net_debt,
        "cash_needed": cash_needed,
        "cash_used": cash_used,
        "new_debt": cash_needed - cash_used,
        "new_shares": paid_in_shares / deal.acquirer_price,
    }


def pro_forma(deal, synergies):
    """Pro forma EPS and accretion for one year, given that year's pre-tax synergies."""
    f = financing(deal)
    keep = 1 - deal.tax_rate
    bridge = {
        f"{deal.target_name} net income": deal.target_net_income,
        f"{deal.target_name} interest saved": deal.target_interest * keep if deal.refinance_target_debt else 0.0,
        "Synergies": synergies * keep,
        "Interest on new debt": -f["new_debt"] * deal.cost_of_debt * keep,
        "Interest lost on cash used": -f["cash_used"] * deal.interest_on_cash * keep,
        "Extra amortisation": -deal.extra_amortisation * keep,
    }
    net_income = deal.acquirer_net_income + sum(bridge.values())
    shares = deal.acquirer_shares + f["new_shares"]
    eps = net_income / shares
    base = standalone_eps(deal)
    return {
        **f,
        "bridge": bridge,
        "net_income": net_income,
        "shares": shares,
        "standalone_eps": base,
        "pro_forma_eps": eps,
        "accretion": eps / base - 1,
    }


def breakeven_synergies(deal):
    """Pre-tax synergies needed for the deal to leave EPS unchanged (0 if it is accretive without any)."""
    result = pro_forma(deal, 0.0)
    needed_net_income = result["standalone_eps"] * result["shares"]
    shortfall = needed_net_income - result["net_income"]
    return max(shortfall / (1 - deal.tax_rate), 0.0)


def valuation(deal):
    """Price paid in multiples, next to the acquirer's own P/E."""
    f = financing(deal)
    return {
        "offer_pe": f["equity_value"] / deal.target_net_income,
        "acquirer_pe": deal.acquirer_price / standalone_eps(deal),
        "ev_ebitda": f["enterprise_value"] / deal.target_ebitda if deal.target_ebitda else float("nan"),
        "ev_ebitda_with_synergies": (f["enterprise_value"] / (deal.target_ebitda + max(deal.synergies.values()))
                                     if deal.target_ebitda else float("nan")),
        # Earnings bought per $1 spent, against what $1 of new debt costs after tax.
        "target_earnings_yield": deal.target_net_income / f["equity_value"],
        "after_tax_cost_of_debt": deal.cost_of_debt * (1 - deal.tax_rate),
    }


def sensitivity(deal, synergies, rows, cols):
    """Accretion for every combination of two inputs.

    rows and cols are (field, values) pairs. The field is any Deal field, or "synergies".
    Returns a list of rows, each a list of accretion values.
    """
    (row_field, row_values), (col_field, col_values) = rows, cols
    table = []
    for r in row_values:
        row = []
        for c in col_values:
            changes = {row_field: r, col_field: c}
            year_synergies = changes.pop("synergies", synergies)
            row.append(pro_forma(with_changes(deal, **changes), year_synergies)["accretion"])
        table.append(row)
    return table
