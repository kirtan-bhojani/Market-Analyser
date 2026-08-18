# Backtesting Pitfalls

Backtesting is the study of how an approach would have behaved on historical data. It is a valuable research tool, but it is easy to produce results that look impressive yet do not hold up, so understanding its common pitfalls is essential to interpreting any backtest honestly.

**Lookahead bias and leakage.** This occurs when a test uses information that would not have been available at the moment of a decision, for example referencing a bar's closing value before the bar has closed, or using a statistic computed over the full dataset including the future. Leakage inflates results because the test effectively "peeks" ahead. Careful attention to the exact timing of every input is the defence.

**Overfitting.** An approach can be tuned so tightly to a specific historical stretch that it captures noise rather than durable behaviour. The more parameters that are adjusted and the more combinations tried, the greater the chance the result reflects coincidence. Overfit approaches typically look excellent in-sample and disappoint out-of-sample.

**Survivorship bias.** Testing only on instruments that still exist today ignores those that were delisted, merged, or failed. Because the failures are missing, the surviving set looks healthier than the real historical universe was, biasing results upward.

**Ignoring fees and slippage.** A backtest that assumes perfect fills at ideal prices omits real transaction costs. Fees and slippage accumulate across many transactions and can turn an apparently profitable study into a losing one, so realistic cost assumptions matter.

**Walk-forward versus random splits.** Because market data is ordered in time, randomly shuffling it into training and testing sets can leak future information into the past. Walk-forward analysis respects chronology by fitting on an earlier window and evaluating on the subsequent one, then rolling forward. This better mimics how an approach would actually be applied through time.

Finally, the most important caveat of all: a favourable backtest describes the past under specific assumptions. Markets change, and past performance does not guarantee or predict future results. A backtest is a source of context and disconfirmation, not a promise.

Educational analysis. Not investment advice. Past performance does not guarantee future results.
