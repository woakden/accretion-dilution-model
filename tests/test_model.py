"""Tests for the accretion/dilution model. Run from the project folder:  python3 -m unittest discover tests"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import model  # noqa: E402
import run  # noqa: E402


def simple_deal(**changes):
    """A small made-up deal with round numbers, easy to check by hand."""
    deal = model.Deal(
        offer_price=20.0, percent_in_shares=0.0, synergies={"Year 1": 0.0}, extra_amortisation=0.0,
        acquirer_net_income=100.0, acquirer_shares=100.0, acquirer_price=15.0, tax_rate=0.25,
        target_net_income=10.0, target_shares=10.0, target_net_debt=0.0, target_interest=0.0,
        target_ebitda=25.0, refinance_target_debt=True,
        cash_used=0.0, cost_of_debt=0.04, interest_on_cash=0.02,
    )
    return model.with_changes(deal, **changes)


class HandCalculations(unittest.TestCase):
    def test_all_debt_deal(self):
        # Equity value 20 x 10 = 200, all borrowed at 4%: interest 8, after 25% tax 6.
        # Net income 100 + 10 - 6 = 104 on 100 shares: EPS 1.04 vs 1.00, so +4%.
        r = model.pro_forma(simple_deal(), 0.0)
        self.assertAlmostEqual(r["new_debt"], 200.0)
        self.assertAlmostEqual(r["pro_forma_eps"], 1.04)
        self.assertAlmostEqual(r["accretion"], 0.04)

    def test_all_share_deal_at_equal_pe_is_neutral(self):
        # Acquirer P/E = 15 / 1.00 = 15x. Paying 15x the target's earnings (price 15) in shares
        # adds earnings and shares in the same proportion, so EPS doesn't change.
        r = model.pro_forma(simple_deal(offer_price=15.0, percent_in_shares=1.0), 0.0)
        self.assertAlmostEqual(r["accretion"], 0.0)

    def test_paying_a_higher_pe_in_shares_is_dilutive(self):
        r = model.pro_forma(simple_deal(offer_price=30.0, percent_in_shares=1.0), 0.0)
        self.assertLess(r["accretion"], 0.0)

    def test_cash_then_debt(self):
        r = model.pro_forma(simple_deal(cash_used=50.0, target_net_debt=40.0), 0.0)
        # Needs 200 for the shares + 40 to repay the target's debt; 50 from cash, 190 borrowed.
        self.assertAlmostEqual(r["cash_used"], 50.0)
        self.assertAlmostEqual(r["new_debt"], 190.0)
        self.assertAlmostEqual(r["enterprise_value"], 240.0)

    def test_cash_used_never_exceeds_what_is_needed(self):
        r = model.pro_forma(simple_deal(cash_used=1000.0), 0.0)
        self.assertAlmostEqual(r["cash_used"], 200.0)
        self.assertAlmostEqual(r["new_debt"], 0.0)

    def test_synergies_and_amortisation_are_taxed(self):
        base = model.pro_forma(simple_deal(), 0.0)["net_income"]
        self.assertAlmostEqual(model.pro_forma(simple_deal(), 8.0)["net_income"] - base, 6.0)
        amortised = model.pro_forma(simple_deal(extra_amortisation=8.0), 0.0)["net_income"]
        self.assertAlmostEqual(base - amortised, 6.0)

    def test_breakeven_synergies_give_zero_accretion(self):
        deal = simple_deal(offer_price=40.0)   # 400 of debt: interest 12 after tax > earnings of 10
        needed = model.breakeven_synergies(deal)
        self.assertAlmostEqual(needed, 2.0 / 0.75)
        self.assertAlmostEqual(model.pro_forma(deal, needed)["accretion"], 0.0)

    def test_no_synergies_needed_when_already_accretive(self):
        self.assertEqual(model.breakeven_synergies(simple_deal()), 0.0)


class CrhArcosa(unittest.TestCase):
    def setUp(self):
        self.deal = model.load(ROOT / "crh_arcosa.json")

    def test_inputs_match_the_announcement(self):
        f = model.financing(self.deal)
        self.assertAlmostEqual(f["equity_value"], 150 * 49.2)
        # CRH quoted an enterprise value of about $8.5bn.
        self.assertAlmostEqual(f["enterprise_value"] / 1000, 8.5, delta=0.2)

    def test_standalone_eps_is_inside_crh_guidance(self):
        self.assertTrue(5.60 <= model.standalone_eps(self.deal) <= 6.05)

    def test_accretion_rises_with_synergies(self):
        acc = [model.pro_forma(self.deal, s)["accretion"] for s in self.deal.synergies.values()]
        self.assertEqual(acc, sorted(acc))

    def test_sensitivity_table_shape_and_base_case(self):
        rows = ("cost_of_debt", [0.04, 0.05, 0.06])
        cols = ("synergies", [0, 60])
        table = model.sensitivity(self.deal, 60, rows, cols)
        self.assertEqual((len(table), len(table[0])), (3, 2))
        self.assertAlmostEqual(table[1][1], model.pro_forma(self.deal, 60)["accretion"])

    def test_report_runs(self):
        text, tables = run.report(self.deal)
        self.assertIn("Synergies needed to break even", text)
        self.assertEqual(len(tables), 3)


if __name__ == "__main__":
    unittest.main()
