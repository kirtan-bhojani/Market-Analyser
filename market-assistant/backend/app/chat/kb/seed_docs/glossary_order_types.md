# Glossary of Order Types

This glossary explains common order types and two related execution concepts. It is descriptive only; this platform is for educational analysis and does not place or manage orders.

**Market order.** An instruction to transact immediately at the best price currently available. Its advantage is a high likelihood of being filled quickly; its trade-off is that the exact fill price is not guaranteed, especially in fast-moving or thin markets.

**Limit order.** An instruction to transact only at a specified price or better. A limit order controls the price but not whether it fills: if the market never reaches the specified level, the order remains unfilled. It is used when price precision matters more than certainty of execution.

**Stop order.** An instruction that stays dormant until price reaches a defined trigger level, at which point it becomes active, typically as a market order. Stop orders are often associated with exiting a position once a threshold is crossed, converting a resting condition into an immediate transaction.

**Stop-limit order.** A variation that, once its stop trigger is reached, activates a limit order rather than a market order. This adds price control at the moment of activation, but it reintroduces the risk that the limit does not fill if price moves through the level too quickly.

**Take-profit order.** A resting order, usually a limit, placed to close a position once a favourable target price is reached. It automates exiting at a predefined objective.

**Slippage.** The difference between the price expected for an order and the price at which it actually transacts. Slippage tends to be larger in volatile or illiquid conditions and is a real cost that analysis should account for, since it can erode results that look clean on paper.

**Fees.** The costs charged to transact, including commissions and, on some venues, spreads or funding-related charges. Like slippage, fees accumulate across many transactions and should be included when evaluating any approach, because ignoring them overstates outcomes.

Educational analysis. Not investment advice. Past performance does not guarantee future results.
