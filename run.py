"""Accretion/dilution model. By default: CRH's acquisition of Arcosa (announced 22 June 2026).

Usage:
    python3 run.py                         # the CRH/Arcosa case in crh_arcosa.json
    python3 run.py --deal my_deal.json     # any other deal in the same format

Prints the deal summary, pro forma EPS for years 1-3 as synergies build up, the synergies needed to
break even, and three sensitivity tables. Saves the same to results/.
"""
import argparse
import csv
from pathlib import Path

import model


def pct(x):
    return f"{x:+.1%}"


def table_text(title, rows, cols, values, row_fmt, col_fmt):
    (row_name, _, row_values), (col_name, _, col_values) = rows, cols
    width = 9
    lines = [title, f"  {row_name} (down) by {col_name} (across)",
             " " * 14 + "".join(f"{col_fmt(c):>{width}}" for c in col_values)]
    for r, line in zip(row_values, values):
        lines.append(f"  {row_fmt(r):<12}" + "".join(f"{pct(v):>{width}}" for v in line))
    return "\n".join(lines)


def save_table(path, rows, cols, values):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"{rows[1]} \\ {cols[1]}"] + list(cols[2]))
        for r, line in zip(rows[2], values):
            w.writerow([r] + [round(v, 5) for v in line])


def report(deal):
    """Return (text, tables) for a deal."""
    years = list(deal.synergies.items())
    first_year = years[0][1]
    last_year = years[-1][1]
    f = model.financing(deal)
    v = model.valuation(deal)
    a, t = deal.acquirer_name, deal.target_name

    def row(label, value):
        return f"  {label + ':':<34}{value}"

    lines = [
        f"{a} acquisition of {t}",
        "",
        "The deal (US$m unless stated)",
        row(f"Offer price per {t} share", f"${deal.offer_price:,.2f}"),
        row("Equity value", f"{f['equity_value']:,.0f}"),
        row(f"{t} net debt taken on", f"{deal.target_net_debt:,.0f}"),
        row("Enterprise value", f"{f['enterprise_value']:,.0f}"),
        row("EV / EBITDA", f"{v['ev_ebitda']:.1f}x before synergies, "
                           f"{v['ev_ebitda_with_synergies']:.1f}x with full synergies"),
        row("Price / earnings paid", f"{v['offer_pe']:.1f}x ({a} trades on {v['acquirer_pe']:.1f}x)"),
        "",
        "Paid for with",
        row(f"{a} cash", f"{f['cash_used']:,.0f}"),
        row(f"New debt at {deal.cost_of_debt:.2%}", f"{f['new_debt']:,.0f}"),
        row(f"New {a} shares issued", f"{f['new_shares']:,.1f}m ({deal.percent_in_shares:.0%} of the price)"),
        "",
        f"Earnings per share ({a} standalone EPS ${model.standalone_eps(deal):.2f})",
        f"  {'':<8}{'Synergies':>10}{'Pro forma EPS':>15}{'Accretion':>11}",
    ]
    for name, syn in years:
        r = model.pro_forma(deal, syn)
        lines.append(f"  {name:<8}{syn:>10,.0f}{r['pro_forma_eps']:>15.2f}{pct(r['accretion']):>11}")

    bridge = model.pro_forma(deal, first_year)["bridge"]
    lines += ["", f"What changes {a}'s net income in {years[0][0]} (after tax, US$m)"]
    lines += [f"  {k:<30}{val:>+9,.1f}" for k, val in bridge.items()]
    lines += [f"  {'Total':<30}{sum(bridge.values()):>+9,.1f}"]

    lines += [
        "",
        f"Synergies needed to break even (pre-tax): {model.breakeven_synergies(deal):,.0f}",
        f"Earnings yield on the purchase price: {v['target_earnings_yield']:.1%}, "
        f"against an after-tax cost of debt of {v['after_tax_cost_of_debt']:.1%}",
    ]

    tables = {
        "1_cost_of_debt_vs_synergies": (
            f"Table 1: {years[0][0]} accretion by cost of new debt and pre-tax synergies",
            ("cost of new debt", "cost_of_debt", [0.04, 0.045, 0.05, 0.055, 0.06]),
            ("synergies", "synergies", [0, 60, 130, 175, 250]),
            first_year, lambda r: f"{r:.1%}", lambda c: f"{c:,.0f}"),
        "2_shares_vs_share_price": (
            f"Table 2: {years[0][0]} accretion by share of the price paid in {a} shares and {a} share price",
            ("% paid in shares", "percent_in_shares", [0.0, 0.25, 0.5, 0.75, 1.0]),
            (f"{a} share price", "acquirer_price", [70.0, deal.acquirer_price, 100.0, 120.0]),
            first_year, lambda r: f"{r:.0%}", lambda c: f"${c:,.2f}"),
        "3_offer_price_vs_amortisation": (
            f"Table 3: {years[-1][0]} accretion by offer price and extra amortisation (pre-tax, US$m)",
            ("offer price", "offer_price", [140.0, 150.0, 160.0, 170.0]),
            ("extra amortisation", "extra_amortisation", [0, 50, 100, 150]),
            last_year, lambda r: f"${r:,.0f}", lambda c: f"{c:,.0f}"),
    }
    computed = {}
    for key, (title, rows, cols, syn, row_fmt, col_fmt) in tables.items():
        values = model.sensitivity(deal, syn, rows[1:], cols[1:])
        computed[key] = (rows, cols, values)
        lines += ["", table_text(title, rows, cols, values, row_fmt, col_fmt)]
    return "\n".join(lines), computed


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--deal", default=str(Path(__file__).with_name("crh_arcosa.json")))
    p.add_argument("--out", default="results")
    args = p.parse_args(argv)

    deal = model.load(args.deal)
    text, tables = report(deal)
    print(text)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.txt").write_text(text + "\n")
    for key, (rows, cols, values) in tables.items():
        save_table(out / f"sensitivity_{key}.csv", rows, cols, values)
    print(f"\nSaved summary.txt and the sensitivity tables in {out}/")


if __name__ == "__main__":
    main()
