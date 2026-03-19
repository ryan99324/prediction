from protocol import Outcome, PredictionProtocol


def print_market_board(proto: PredictionProtocol, title: str) -> None:
    print("\n" + title)
    print("-" * len(title))
    for row in proto.market_snapshot():
        print(
            f"{row['market_id']} | {row['category']} | P(YES)={row['p_yes']:.2%} | "
            f"YES_shares={row['q_yes']:.1f} NO_shares={row['q_no']:.1f}"
        )


def main() -> None:
    proto = PredictionProtocol()

    # 1) Create strategic markets
    proto.create_market(
        market_id="MNA_2026_Q4",
        title="Acquisition X reaches >= 12% ROI by 12 months",
        category="M&A",
        liquidity_b=120,
        fee_bps=30,
    )
    proto.create_market(
        market_id="PMF_MOBILE_AUG",
        title="New mobile feature reaches PMF criteria by Aug 2026",
        category="Product-Market-Fit",
        liquidity_b=100,
        fee_bps=25,
    )
    proto.create_market(
        market_id="Q3_REV_TARGET",
        title="Q3 revenue meets or exceeds internal target",
        category="Quarterly Target",
        liquidity_b=140,
        fee_bps=20,
    )

    # 2) Fund internal participants with tokens
    for trader in ["finance_lead", "product_mgr", "sales_director", "corp_dev"]:
        proto.fund_trader(trader, tokens=500.0)

    print_market_board(proto, "Initial Market Board")

    # 3) Place trades (confidence expressed as stake + direction)
    proto.place_trade("MNA_2026_Q4", "corp_dev", Outcome.YES, shares=35)
    proto.place_trade("MNA_2026_Q4", "finance_lead", Outcome.NO, shares=12)

    proto.place_trade("PMF_MOBILE_AUG", "product_mgr", Outcome.YES, shares=28)
    proto.place_trade("PMF_MOBILE_AUG", "sales_director", Outcome.NO, shares=20)

    proto.place_trade("Q3_REV_TARGET", "sales_director", Outcome.YES, shares=45)
    proto.place_trade("Q3_REV_TARGET", "finance_lead", Outcome.NO, shares=30)

    print_market_board(proto, "After Trading")

    # 4) Probability-weighted planning metrics
    expected_roi = proto.expected_mna_roi(
        market_id="MNA_2026_Q4",
        success_roi=0.18,   # 18% ROI if successful integration
        failure_roi=-0.04,  # -4% ROI if underperforming
    )
    expected_q3_rev = proto.expected_quarterly_revenue(
        market_id="Q3_REV_TARGET",
        on_target_revenue=1_250_000_000,
        miss_revenue=1_080_000_000,
    )

    print("\nDecision Support Outputs")
    print("------------------------")
    print(f"Expected M&A ROI (probability-weighted): {expected_roi:.2%}")
    print(f"Expected Q3 revenue (probability-weighted): ${expected_q3_rev:,.0f}")

    # 5) Resolve market to demonstrate settlement
    proto.resolve_market("MNA_2026_Q4", Outcome.YES)

    print("\nAccount Balances After M&A Resolution")
    print("--------------------------------------")
    for row in proto.account_snapshot():
        print(f"{row['trader_id']}: {row['token_balance']:.2f} tokens")


if __name__ == "__main__":
    main()
