# ML / DL Deep Dive — Market Analysis Assistant

This is a **self-contained** study guide for the machine-learning and deep-learning pieces of this repository. You do not need the general project document. After you finish it, you should be able to explain, debug, modify, and defend the ML system in an interview.

**How this document labels knowledge**

| Label | Meaning |
| --- | --- |
| **Verified from code** | Observed in source, tests, or config. |
| **Reasonable inference** | Technically sound explanation the repo does not prove. |
| **Unknown** | Cannot be determined from the repository. |

---

# The one sentence you must not get wrong

This project **does not train a neural network**.

The **trading signal model** is a **LightGBM gradient-boosted tree classifier** on hand-built OHLCV features.

Deep learning **is** used, but only as **frozen pretrained models**:

1. **FinBERT** (`transformers` + PyTorch under the hood) scores news headlines.
2. **BGE-small** (`sentence-transformers` + PyTorch) embeds knowledge-base text for RAG.

If an interviewer says “walk me through your PyTorch training loop,” the correct answer is:

> We don’t have one. LightGBM’s `fit()` trains the signal model. We only *load* Hugging Face models for sentiment and embeddings, on CPU, with no fine-tuning in this repo.

That honesty is stronger than pretending you built an LSTM.

---

# Table of contents

1. [What role ML/DL plays](#1-what-role-mldl-plays)
2. [The actual pipeline](#2-the-actual-pipeline)
3. [Prerequisites](#3-mldl-prerequisites)
4. [Concepts used (and not used)](#4-every-mldl-concept-this-project-uses)
5. [Data: from candles to a row](#5-data-from-raw-candles-to-a-model-row)
6. [Labels](#6-labels--what-the-model-is-trying-to-predict)
7. [Leakage and walk-forward](#7-leakage-and-purged-walk-forward)
8. [Model: LightGBM](#8-model-lightgbm-the-trading-classifier)
9. [Loss](#9-the-loss-function)
10. [How trees “optimize” (not Adam)](#10-how-training-actually-updates-the-model)
11. [Calibration](#11-probability-calibration-isotonic-regression)
12. [Evaluation and the publish gate](#12-evaluation-and-the-publish-gate)
13. [Inference in production](#13-inference-in-production)
14. [Hyperparameters](#14-hyperparameters)
15. [Tensor / array shapes](#15-array--tensor-shape-walkthrough)
16. [DL system 1: FinBERT](#16-deep-learning-system-1--finbert-sentiment)
17. [DL system 2: BGE embeddings + RAG](#17-deep-learning-system-2--bge-embeddings--rag)
18. [Tools](#18-tools-and-libraries)
19. [Modelling decisions](#19-modelling-decisions)
20. [Failure modes and debugging](#20-failure-modes-and-debugging)
21. [Interview questions and answers](#21-mldl-interview-questions-and-answers)
22. [Whiteboard scripts](#22-explain-this-on-a-whiteboard)
23. [Unified mental model](#23-unified-mental-model)
24. [Study order](#24-recommended-study-order)
25. [Checklists](#25-defense-checklist)

---

# 1. What role ML/DL plays

## The product context (minimum you need)

The app is an **analysis-only** market assistant: crypto candles (Binance) and delayed Indian equities live in Postgres. Rule-based **strategies** already emit signals. ML is an extra signal source: “given the last few bars’ statistics, how likely is the next horizon to be up?”

It does **not** place trades. A model output becomes a row in `signals` with `strategy="ml_lgbm_v1"` and `direction="long"`.

## Three separate ML problems

```text
┌─────────────────────────────────────────────────────────────┐
│  A. TRADING CLASSIFIER (trained in this repo)               │
│     Input:  7 numeric features from OHLCV                   │
│     Output: P(close[t+h] > close[t])  then long-or-nothing  │
│     Model:  LightGBM + isotonic calibrator                  │
│     Code:   app/ml/*                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  B. NEWS SENTIMENT (pretrained, inference only)             │
│     Input:  headline strings                                │
│     Output: score in [-1, 1] = P(pos) - P(neg)              │
│     Model:  ProsusAI/finbert via transformers.pipeline      │
│     Code:   app/ingest/sentiment.py                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  C. TEXT EMBEDDINGS FOR RAG (pretrained, inference only)    │
│     Input:  markdown chunks / user query                    │
│     Output: 384-d unit vectors                              │
│     Model:  BAAI/bge-small-en via sentence-transformers     │
│     Code:   app/chat/kb/embedder.py, kb_tools.py            │
└─────────────────────────────────────────────────────────────┘
```

## Why ML is needed (trading)

Rule strategies answer “did RSI cross 30?” ML answers a different question: **“historically, did this *combination* of returns, volatility, RSI, volume, and VWAP distance precede an up-move often enough to beat buy-and-hold after fees?”**

That is a **supervised binary classification** problem on **time-ordered** bars.

**Reasonable inference:** The team did not want a neural net that memorizes recent crypto noise. They wanted a small tree model, leakage guards, and a **publish gate** so a weak model never reaches the live worker.

## Why DL is needed (sentiment + RAG)

- Headlines are **language**. Trees on OHLCV cannot score “Fed hikes rates.” FinBERT is a BERT classifier trained on financial phrasebank-style data (**Reasonable inference** about FinBERT’s original training; this repo only *calls* the Hub model).
- Chat needs **semantic search** over educational docs, not keyword match. Dense embeddings + cosine distance in pgvector solve that.

## Where models sit in the application

```text
Binance / equity poller
        ↓
   candles table
        ↓
  1h bar closes  ──────────────────────────────┐
        ↓                                      │
dispatch_close_jobs                            │
        ↓                                      │
run_ml_inference_job                           │
        ↓                                      │
 LightGBM.predict_proba + isotonic             │
        ↓                                      │
 if published AND p ≥ threshold                │
        ↓                                      │
   signals row + UI / WS                       │
                                               │
RSS headlines ─► FinBERT ─► news_items.sentiment
                                               │
seed_docs ─► chunk ─► BGE encode ─► kb_chunks
user query ─► BGE encode ─► cosine top-k ─► LLM tool
```

**Before the trading model:** ingest, aggregation to 1h, load last 250 bars.

**After the trading model:** optional `Signal` insert; frontend `/ml/:id` shows metrics if a row exists. The list page `/ml` currently shows an **empty state** saying models appear “once trained and published” (**Verified:** `frontend/src/pages/ML.tsx`). Detail page `/ml/:id` **is** wired to `GET /ml/models/{id}`.

---

# 2. The actual pipeline

Replace the generic “epochs / backprop” cartoon with what the code does.

## Trading model (LightGBM)

```text
OHLCV candles (Postgres)
   ↓  pandas DataFrame columns o,h,l,c,v indexed by ts
build_features()                    app/ml/features.py
   ↓  rolling returns, RSI, vol, volume z, VWAP distance
   ↓  dropna (warmup)
build_fixed_horizon_labels()        app/ml/labels.py
   ↓  y = 1{ close[t+h] > close[t] }, label_ts = t+h
inner join on timestamp
   ↓
assert_no_leakage                   app/backtest/leakage.py
   ↓  require feature_ts < label_ts
FEATURE_COLUMNS select (7 cols)     app/ml/train.py
   ↓
purged_walk_forward_splits          app/ml/splitter.py
   ↓  require purge ≥ horizon
assert_no_cross_fold_leakage
   ↓
for each fold:
   LGBMClassifier.fit(X_train, y_train)
   predict_proba(X_test)[:, 1]
   record fold accuracy
   ↓
out-of-fold raw probabilities
   ↓
split OOF in half
   fit IsotonicRegression on earlier OOF
   apply to later OOF                 app/ml/calibration.py
   ↓
entries = calibrated_p ≥ threshold (default 0.55)
   ↓
simulate_directional_returns        app/ml/evaluate.py
   vs buy_and_hold_return
   vs random_baseline_return (same trade count)
   ↓
published = model > both baselines  app/ml/baseline.py
   ↓
fit final LightGBM on ALL X, y
pickle {model, calibrator}          app/ml/registry.py
```

**Stages that do NOT exist for this model (Verified):**

- No tokenization
- No `nn.Module`, no `loss.backward()`, no Adam, no epochs loop in our code
- No GPU training
- No train HTTP endpoint — `train_model()` is a library function used by **tests** (`tests/integration/test_ml_train_job.py`, acceptance tests). **Unknown:** whether anyone runs it as a manual script in production.

## Live inference (after a model is published)

```text
1h candle commit
   ↓
dispatch: if tf=="1h" and published MLModel for instrument_group
   ↓
load last 250 1h bars (skip if < 30)
   ↓
enqueue run_ml_inference_job(model_id, instrument_id, window_df)
   ↓
load pickle → build_features → last row → predict_prob_up
   ↓
threshold from ml_models.metrics["threshold"]  (asserted, not defaulted)
   ↓
Redis SET NX dedup → INSERT signals
```

**Verified constants** in `app/ingest/dispatch.py`:

| Name | Value | Meaning |
| --- | --- | --- |
| `ML_INFERENCE_TF` | `"1h"` | Only 1h closes trigger ML |
| `ML_WINDOW_BARS` | `250` | History shipped to the job |
| `MIN_ML_BARS` | `30` | Below this, features would be empty after warmup |

## Sentiment pipeline

```text
RSS items
   ↓
score_batch(titles)   # FinBERT, CPU, batch 16
   ↓
news_items.sentiment = P(positive) - P(negative)
```

## Embedding / RAG pipeline

```text
seed markdown (max ~200 words/chunk)
   ↓
SentenceTransformer.encode(..., normalize_embeddings=True)
   ↓
kb_chunks.embedding VECTOR(384)
   ↓ at query time
embed query → ORDER BY cosine_distance LIMIT k (default 4)
```

---

# 3. ML/DL prerequisites

Study **in this order**. Depth is calibrated to *this* repo.

```text
Supervised learning (classification)
   ↓
Time series: why random K-fold is cheating
   ↓
Feature engineering on OHLCV (returns, RSI, z-scores)
   ↓
Decision trees
   ↓
Gradient boosting / LightGBM
   ↓
Log loss + predicted probabilities
   ↓
Isotonic calibration
   ↓
Walk-forward + purge (leakage)
   ↓
Economic evaluation (costs, baselines)
        ── parallel track for DL ──
Linear algebra (vectors, cosine)
   ↓
Transformer encoder (BERT) at “what a token embedding is” depth
   ↓
Hugging Face pipeline / sentence-transformers (inference only)
```

### Essential

| Topic | Why | Depth | Where it appears |
| --- | --- | --- | --- |
| Binary classification | `y ∈ {0,1}` | You can write the label definition | `labels.py` |
| Time-series leakage | Interview #1 | `feature_ts < label_ts`, purge | `leakage.py`, `train.py` |
| Gradient boosting | The model | Intuition + one boosting step | `LGBMClassifier` |
| Log loss | Default LightGBM binary objective | Formula + tiny example | not explicit in our code; library default |
| Probability vs decision | threshold 0.55 | `should_emit_signal` | `inference.py` |
| Rolling features / NaN warmup | `dropna` drops early bars | `features.py` | |
| Transaction costs in bps | Gate is economic, not accuracy | `costs.py`, `evaluate.py` | |

### Important

| Topic | Why | Depth |
| --- | --- | --- |
| Isotonic regression | Shipped calibrator | PAVA intuition, clip to [0,1] |
| Feature importance (split gain) | UI chart | LightGBM `feature_importances_` |
| Cosine similarity | RAG | unit vectors, `1 - cosine` as distance |
| BERT classification head | FinBERT | tokens → [CLS] → softmax over labels |
| Train/serve skew | regime columns excluded | comment in `train.py` |

### Useful

| Topic | Why | Depth |
| --- | --- | --- |
| Triple-barrier labels | Code exists, **not used in `train_model`** | Know the algorithm so you don’t over-claim |
| Histogram approximation in LightGBM | Why it’s fast | High-level |
| GELU / self-attention | Only if they drill FinBERT | Sketch, not derivations |
| PyTorch autograd | We never call it | Know it exists *inside* `transformers` |

**Do not start with LSTM, CNN, GAN, or a custom Adam loop.** Those are not this project.

---

# 4. Every ML/DL concept this project uses

## Used

- Supervised **binary classification**
- **Feature engineering** (lags, rolling std, RSI, volume z, VWAP distance)
- **Missing-value warmup** (`dropna`)
- **Decision trees** and **gradient boosting** (LightGBM)
- **Predicted probabilities** (`predict_proba`)
- **Log loss** (LightGBM binary default — **Reasonable inference:** `LGBMClassifier` uses `binary` objective / log loss unless overridden; this repo does not pass `objective=`)
- **Learning rate** as shrinkage (`learning_rate=0.05`)
- **Regularization via small trees** (`num_leaves=15`, `n_estimators=100`)
- **Random seed** (`random_state=42`)
- **Accuracy** (fold metric only)
- **Isotonic calibration**
- **Purged walk-forward CV**
- **Lookahead leakage** checks
- **Class decision threshold** (0.55, stored in metrics)
- **Baseline models** (buy-and-hold, random entries)
- **Cost-aware evaluation** (fees + slippage)
- **Feature importances**
- **Model registry** (DB row + pickle)
- **Grouped models** (`crypto_majors` / `crypto_alts` / `nse_equities`)
- **Pretrained transformers** (FinBERT)
- **Sentence embeddings** (BGE)
- **Cosine nearest neighbors** (pgvector)
- **Chunking** for RAG
- **Normalization of embeddings** (`normalize_embeddings=True`)

## Directly necessary to defend a decision (even if not imported)

- **Overfitting** on finance time series
- **Distribution shift** (regime change)
- **Class imbalance** (up vs down days — not explicitly reweighted in code)
- **Why not neural nets / LSTM / Transformer on prices**

## Not used (do not study as if they were)

- CNN, RNN/LSTM/GRU **on this repo’s trained model**
- GANs, autoencoders
- Dropout, batch norm, Adam, SGD in *our* training code
- `DataLoader`, `nn.Module`, CUDA device moves
- TensorBoard, W&B, ONNX, TorchScript
- SVM, k-NN, Naive Bayes, logistic regression as the production classifier
- Fine-tuning BERT
- Triple-barrier **in the trainer** (function exists; `train_model` calls `build_fixed_horizon_labels` only)

---

# 5. Data: from raw candles to a model row

## Concept → intuition

A candle is one bar: open, high, low, close, volume. The model never sees the raw sequence of 250 closes as a “sentence.” It sees **seven numbers that summarize recent behavior** on *this* bar.

That is **tabular ML**, not sequence DL.

## Mathematics of the features

Let \(C_t, H_t, L_t, V_t\) be close, high, low, volume.

**Returns (lags 1, 3, 5)** — `ret_k = close.pct_change(k)`:

\[
r_t^{(k)} = \frac{C_t}{C_{t-k}} - 1
\]

**Example.** \(C_{t-1}=100\), \(C_t=102\):

\[
r_t^{(1)} = 0.02
\]

**Realized volatility** — `vol_10` = rolling std of 1-bar returns, window 10:

\[
\sigma_t = \mathrm{std}(r_{t-9}^{(1)}, \ldots, r_t^{(1)})
\]

**RSI(14)** — Wilder-style *simplified* to SMA of gains/losses in this code (not classic Wilder EMA). **Verified:** `_rsi` uses `rolling(window).mean()` on gains and losses.

\[
\begin{aligned}
\Delta_t &= C_t - C_{t-1} \\
G_t &= \max(\Delta_t, 0),\quad L_t = \max(-\Delta_t, 0) \\
\mathrm{RS} &= \bar G / \bar L \\
\mathrm{RSI} &= 100 - \frac{100}{1+\mathrm{RS}}
\end{aligned}
\]

Edge cases **in code**: if avg loss is 0, RSI → 100; 0/0 → fill 50 on flat; warmup stays NaN.

**Volume z-score** (window 20):

\[
z_t = \frac{V_t - \mu_{V,20}}{\sigma_{V,20}}
\]

If \(\sigma=0\) (flat volume), **set z = 0** rather than NaN — otherwise `dropna` would delete the latest bar and **serve-time `iloc[-1]` would be the previous bar** (comment in `features.py`).

**VWAP distance** (window 20). Typical price \(T_t = (H_t+L_t+C_t)/3\):

\[
\mathrm{VWAP}_t = \frac{\sum T_i V_i}{\sum V_i},\quad
d_t = \frac{C_t - \mathrm{VWAP}_t}{\mathrm{VWAP}_t}
\]

Zero volume sum → distance 0; inf → 0.

**Regime one-hots** are computed if a `regime` series is passed, categories `trend_up`, `trend_down`, `range`, `high_vol`. They are **not** in `FEATURE_COLUMNS`. Inference calls `build_features(candles_window)` **without** regime, so those columns would be zeros anyway. Training with real regime dummies and serving zeros would be **train/serve skew**. The code prevents that by never selecting them.

## Before / after example

Suppose 5 bars (too short to survive RSI warmup — illustration of *shape* only):

```text
ts     c      v
t0     100    1000
t1     101    1100
t2     100    900
t3     103    1200
t4     104    1300
```

`ret_1` at t4 = 104/103 - 1 ≈ 0.0097.

After full warmup (~20 bars for volume/VWAP, 14 for RSI), each kept row is:

```text
[ret_1, ret_3, ret_5, vol_10, rsi_14, volume_z, vwap_dist]
dtype: float64
shape: (1, 7)   # one bar at inference
       (n, 7)   # training matrix
```

**No standardization / StandardScaler** is applied. Trees split on thresholds, so feature scale is less critical than for neural nets. **Verified:** no scaler in `app/ml/`.

## Leakage risk in preprocessing?

Rolling features use **past and current** bars only (`pct_change`, `rolling`). They do not use future closes. Labels *do* use the future — that is why `label_ts` is stored and compared.

`dropna` after rolling is required: early rows are not valid features. It is **not** leakage; it shortens the sample.

Could it cause leakage? Only if you accidentally rolling-window with `center=True` (future in the window). This code does **not**.

---

# 6. Labels — what the model is trying to predict

## Fixed horizon (what training uses)

**File:** `app/ml/labels.py` → `build_fixed_horizon_labels`

\[
y_t = \mathbf{1}\{ C_{t+h} > C_t \}
\]

`label_ts` = timestamp of bar \(t+h\).

**Example.** Horizon \(h=1\), closes `[100, 102, 101]`:

| t | C | C_{t+1} | y |
| --- | --- | --- | --- |
| 0 | 100 | 102 | 1 |
| 1 | 102 | 101 | 0 |
| 2 | 101 | — | dropped |

Interview phrasing: “We predict **direction of the close h bars ahead**, not the size of the move, not a stop-out.”

**Limitation:** a +0.01% up-move and a +10% up-move are the same `y=1`. The **publish gate** later cares about *return after costs*, which *does* care about size.

## Triple barrier (implemented, not wired to `train_model`)

**File:** same, `build_triple_barrier_labels`

From bar \(t\), look at highs/lows of \(t+1 \ldots t+h\):

- Hit \(+tp\%\) first → \(y=1\)
- Hit \(-sl\%\) first → \(y=0\)
- Both same bar → **y=0** (conservative)
- Neither → \(y = \mathbf{1}\{C_{t+h} > C_t\}\)

**Verified:** unit tests call this; `train_model` does **not**.

If asked “why not triple barrier?”:

> The repository does not record the product reason. A technically reasonable explanation: fixed horizon is simpler to align with `simulate_directional_returns(..., horizon=h)`, which always exits after h bars. Triple-barrier labels would disagree with that simulator unless you also change evaluation.

---

# 7. Leakage and purged walk-forward

This is the **core ML interview** for the trading model.

## Concept

If the label at time \(t\) uses \(C_{t+h}\), then any training row whose label timestamp lands **inside** the test window has already “seen” test-period prices.

## Check 1 — row alignment

`assert_no_leakage` requires `feature_ts < label_ts` on every paired row.

**Tiny example.** Feature at 10:00, label uses 11:00 close → OK. Feature at 11:00, label_ts 11:00 → **LeakageError**.

## Check 2 — purge ≥ horizon

In `train_model`:

```text
if purge < horizon: raise ValueError
```

**Why.** Last training row’s label looks `horizon` bars into the future. If test starts immediately after train, that label overlaps test.

## Check 3 — walk-forward splits

`purged_walk_forward_splits(n_samples, n_splits, test_size, purge)`:

```text
k = 0,1,...,n_splits-1
train_end = initial_train_size + k * test_size
test_start = train_end + purge
test_end = test_start + test_size
train = [0, train_end)          # expanding window
test  = [test_start, test_end)
```

Default `initial_train_size = test_size`.

**Picture** (`test_size=8`, `purge=1`, `n_splits=3`) as in tests:

```text
Fold 0: train [0,8)   gap 8   test [9,17)
Fold 1: train [0,16)  gap 16  test [17,25)
Fold 2: train [0,24)  gap 24  test [25,33)
```

This is **not** sklearn `TimeSeriesSplit` (no purge). It is a custom expander + embargo.

## Check 4 — cross-fold leakage

`assert_no_cross_fold_leakage`: max `label_ts` in train < min `feature_ts` in that fold’s test.

Defense in depth if someone passes `purge` incorrectly relative to timestamps (not just index counts).

## Why not random 80/20?

Shuffling bars would put Tuesday morning in train and Tuesday afternoon in test while they share the same trend. Accuracy would look great and be **meaningless**.

---

# 8. Model: LightGBM (the trading classifier)

## 1. Why it exists

Produce \(P(y=1 \mid x)\) from 7 numeric features, cheaply, on CPU, with a model small enough to pickle and load in an arq worker.

## 2. Problem it solves

Tabular binary classification on a **short, noisy, dependent** sample of hourly bars.

## 3. Input

`pandas.DataFrame` with `FEATURE_COLUMNS`, one row per valid bar.

At serve: `features[FEATURE_COLUMNS].iloc[[-1]]` — a **one-row** frame so column names are preserved (LightGBM can use named features).

## 4. Output

- `predict_proba` → shape `(n, 2)` columns `[P(y=0), P(y=1)]`
- We take `[:, 1]` as raw \(p_{\mathrm{up}}\)
- Isotonic maps it to calibrated \(p\)
- If \(p \ge \tau\) and `published`, emit long

## 5. Architecture (draw this)

LightGBM is **not** layers of neurons. It is an **additive ensemble of decision trees**:

```text
x (7 numbers)
    │
    ├─► Tree 1  ──► f1(x)   (a number: leaf score)
    ├─► Tree 2  ──► f2(x)
    ├─► ...
    └─► Tree T  ──► fT(x)     T = n_estimators = 100
                    │
                    Σ  F(x) = f1 + lr * f2 + ...   (schematic)
                    │
                    σ(F(x)) → P(y=1)
```

Each tree is grown **leaf-wise** with at most `num_leaves=15` leaves (LightGBM’s characteristic vs sklearn’s depth-wise trees).

**Reasonable inference of binary mapping:** LightGBM converts the sum of leaf scores through a sigmoid for `binary` objective:

\[
p = \frac{1}{1+e^{-F(x)}}
\]

Our repo never writes that sigmoid; the library does.

## 6. Mathematical intuition — one boosting step

You are fitting

\[
F_{m}(x) = F_{m-1}(x) + \eta \, h_m(x)
\]

where \(h_m\) is a new tree that fits the **negative gradient** of log loss w.r.t. \(F_{m-1}\). For log loss, that gradient at a point is essentially \(p - y\) (residual). The new tree tries to predict those residuals, then they are **shrunk** by \(\eta = 0.05\).

**Toy numbers (hand-calculable, schematic):**

Suppose one feature \(x=\mathrm{rsi}\), true \(y=1\), current \(F=0\) so \(p=0.5\).

Residual \(y-p = 0.5\). A stump says “if RSI < 30, add +1.2 else add −0.3”. Shrinkage 0.05: if RSI=25, new \(F = 0 + 0.05 \times 1.2 = 0.06\), \(p \approx 0.515\). After many trees, \(p\) can move toward 0 or 1.

This **is** gradient descent in **function space**, not in a neural weight matrix. If asked “where is backprop?”: **there isn’t any in our trainer.** Boosting uses gradients of the loss w.r.t. the current prediction, then fits a tree. No chain rule through layers.

## 7. Step-by-step example (project domain)

Bar just closed on `BTC/USDT` 1h:

```text
ret_1 = +0.4%
ret_3 = -1.1%
ret_5 = +0.2%
vol_10 = 0.008
rsi_14 = 28
volume_z = +1.7
vwap_dist = -0.003
```

LightGBM walks each of 100 trees, sums leaf values, sigmoid → raw p = 0.62. Isotonic (learned on OOF) might map 0.62 → 0.58. Threshold 0.55 → **emit long**. Confidence stored as 0.58.

## 8. Training (actual code)

```python
clf = lgb.LGBMClassifier(
    n_estimators=100,
    num_leaves=15,
    learning_rate=0.05,
    random_state=42,
)
clf.fit(X.iloc[train_idx], y[train_idx])
raw_test = clf.predict_proba(X.iloc[test_idx])[:, 1]
```

There is **no** epoch loop in `train.py`. `n_estimators=100` **is** the number of boosting rounds (the analogue of “how many additive steps”).

Final model: `final_model.fit(X, y)` on **all** labeled rows after CV. That is a common pattern: CV for **honest metrics and gate**, then refit for **capacity**. Risk: the shipped model is slightly more fit to the whole sample than fold models. The **gate** still used held-out OOF for economic simulation.

## 9. Inference

`predict_prob_up` in `inference.py`:

```python
raw = model.predict_proba(features_row)[:, 1]
if calibrator is None:
    return float(raw[0])
return float(apply_calibrator(calibrator, raw)[0])
```

Calibrator is `None` if OOF raw probabilities were constant (cannot fit isotonic).

## 10. Hyperparameters (see table in §14)

## 11. Implementation files

| Piece | Path |
| --- | --- |
| Factory | `default_lgbm_classifier` in `train.py` |
| Feature list | `FEATURE_COLUMNS` |
| Train | `train_model` |
| Serve | `workers/ml_inference_worker.py` |
| Artifact | `registry.py` pickle dict `{"model", "calibrator"}` |

## 12. Line-by-line (the important ones)

- `features.join(labels, how="inner")` — only rows with both valid features and a future label.
- `orig_pos = candles.index.get_indexer(joined.index)` — map filtered rows back to **full** close series so exiting `horizon` bars later means **real bars**, not “horizon rows after dropna gaps.”
- Fold accuracy uses **raw** 0.5-threshold preds, **not** the 0.55 economic threshold. **Verified.** Don’t confuse UI fold accuracy with the publish rule.
- `split = len(oof_idx) // 2` — first half OOF fits isotonic; second half evaluates the gate. Prevents calibrator overfitting the same points it is judged on (comment T3-5).
- Shipped calibrator **is** the gate calibrator — no second fit that would mismatch serve vs gate.

## 13. Why this architecture

**Verified comments:** regime features excluded for serve parity; threshold must live in metrics.

**Reasonable inference for LightGBM:**

- Hundreds-to-thousands of hourly bars, 7 features → trees work; Transformers on 7 scalars are overkill
- CPU-only worker (HF Space, `device=-1` elsewhere shows CPU bias)
- Missingness/warmup handled by dropna; trees handle nonlinear interactions (RSI × volume z) without manual crosses
- Fast `fit` in tests with tiny `n`

## 14. Alternatives

| Alternative | Tradeoff |
| --- | --- |
| Logistic regression | Interpretable; misses interactions unless you engineer them |
| Random forest | Less sequential residual fitting; often similar |
| XGBoost / CatBoost | Similar class; LightGBM is the one pinned |
| LSTM on raw closes | Needs more data, leakage-prone windows, GPU, harder serve |
| Transformer on ticks | Absurd for this universe size |
| Don’t use ML | Only rule strategies — the product already has those |

## 15. Limitations

- Long-only
- Fixed-horizon labels ignore stop-outs
- Group models (`crypto_alts`) pool many coins — **heterogeneity**
- No hyperparameter search in repo
- Accuracy can be ~50% in markets and still “publish” if the **economic** gate passes (or fail despite decent accuracy)
- Pickle + LightGBM version coupling

## 16. Interview questions (see §21)

---

# 9. The loss function

## What the code actually specifies

`train.py` does **not** pass `objective=` or a sklearn `loss`.

**Reasonable inference (LightGBM docs, not this file):** `LGBMClassifier` default objective is **binary log loss** (logistic).

\[
L = -\frac{1}{n}\sum_i \Big[ y_i \log p_i + (1-y_i)\log(1-p_i) \Big]
\]

## Intuition

If \(y=1\) and you predicted \(p=0.9\), loss is small (\(-\log 0.9 \approx 0.105\)). If you predicted \(p=0.1\), loss is large (\(-\log 0.1 \approx 2.3\)).

## Tiny example

\(y=1\), \(p=0.55\): \(L = -\log(0.55) \approx 0.598\).

After trees push \(p\) to \(0.80\): \(L \approx 0.223\).

## Why log loss (not MSE, not hinge) for this project

We need **probabilities** for a threshold and for isotonic calibration. MSE on `{0,1}` is possible (Brier) but is not LightGBM’s binary default. Hinge loss (SVM) does not output well-calibrated probabilities.

**What if we used MSE on prices?** That would be **regression** of future return, a different product. The code is classification.

## Where it appears

Inside `clf.fit(...)`. You will not find `criterion = nn.CrossEntropyLoss()` anywhere in `app/ml/`.

## Gradients

For one example, \(\frac{\partial L}{\partial F} = p-y\) if \(p=\sigma(F)\). LightGBM uses that (and Hessian \(p(1-p)\)) to grow trees. **We do not implement this.**

## Separate “loss” used for **publishing**

The **gate** does **not** use log loss. It uses **compounded net trading return** vs baselines. A model can have OK log loss and still fail the gate (too few trades, costs eat the edge).

---

# 10. How training actually updates the model

## If you expected this

```python
optimizer.zero_grad()
loss.backward()
optimizer.step()
```

**That loop is not in this repository** for the trading model.

## What to say instead

**Optimization method:** gradient boosting (functional gradient descent) implemented by LightGBM’s histogram algorithm.

**Learning rate \(\eta=0.05`:** each new tree’s contribution is shrunk. Too high (e.g. 0.5): overfit, jagged probabilities. Too low (e.g. 0.001) with only 100 trees: underfit, p stuck near base rate.

**There is no Adam, momentum, or weight decay in our `LGBMClassifier` kwargs.** LightGBM *has* `lambda_l1` / `lambda_l2` but we don’t set them (library defaults apply — **Unknown** exact default without checking the installed LightGBM version).

**`random_state=42`:** feature/data sampling reproducibility, not “Adam beta.”

### Tiny boosting update (verbal whiteboard)

1. Start with \(F=\) log-odds of class prior.
2. Compute \(p_i=\sigma(F_i)\), residuals \(y_i-p_i\).
3. Fit tree \(h\) to residuals (approx.).
4. \(F \leftarrow F + 0.05\, h\).
5. Repeat 100 times.

### What would “backprop” mean if they insist?

Only inside **FinBERT / BGE**, which were trained by *other people* with Adam + cross-entropy on text. We load weights; we do not run `backward()`.

---

# 11. Probability calibration (isotonic regression)

## Why

Tree ensembles often produce **overconfident** or poorly ranked probabilities. A 0.9 from LightGBM may not mean “90% of those bars went up.”

The **decision threshold 0.55** is only meaningful if \(p\) is on a reasonable scale.

## Mathematics (intuition, not a full PAV proof)

Isotonic regression finds a **nondecreasing** step function \(c: [0,1]\to[0,1]\) minimizing \(\sum_i (c(p_i)-y_i)^2\) with \(c(p_i) \le c(p_j)\) whenever \(p_i \le p_j\).

sklearn: `IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)`.

`apply_calibrator` clips predictions to [0,1] again.

## Example

Raw p: `0.2, 0.4, 0.8`  
Labels: `0, 1, 1`  
Isotonic might map 0.2→0.0, 0.4→0.5, 0.8→1.0 (illustrative).

## Project-specific protocol

OOF predictions from all folds are concatenated. **Earlier half** of OOF time fits \(c\); **later half** is used for the economic gate with \(c(p)\). Same \(c\) is pickled.

If all raw values are identical, isotonic is skipped (`gate_calibrator = None`).

## Interview

“Did you use Platt scaling (logistic on scores)?” — No. Isotonic. More flexible, needs enough OOF points; can overfit if you calibrate and test on the same OOF (they split to avoid that).

---

# 12. Evaluation and the publish gate

## Fold metric: accuracy

\[
\mathrm{acc} = \frac{1}{n_{\mathrm{test}}}\sum \mathbf{1}\{\hat y_i = y_i\},\quad \hat y = \mathbf{1}\{p_{\mathrm{raw}} \ge 0.5\}
\]

**Why accuracy is weak here:** if 52% of hours are up, a dummy “always up” scores 52%. Markets are close to 50/50. **The product therefore does not publish on accuracy.**

UI still shows per-fold accuracy (`MLModels.tsx` table).

## Economic metric (what actually matters)

For entries where calibrated \(p \ge 0.55\) on the **eval OOF slice**, mapped back to full close array:

Hold **exactly `horizon` bars**, **non-overlapping** (if you enter at i, next candidate is i+horizon).

Net return of one trade (`apply_costs`, long):

Slippage fraction \(s = \mathrm{bps}/10^4\), fee fraction \(f\) likewise.

\[
\begin{aligned}
P_{\mathrm{in}} &= C_{\mathrm{entry}}(1+s) \\
P_{\mathrm{out}} &= C_{\mathrm{exit}}(1-s) \\
\mathrm{gross} &= P_{\mathrm{out}}-P_{\mathrm{in}} \\
\mathrm{fees} &= f(P_{\mathrm{in}}+P_{\mathrm{out}}) \\
\mathrm{net} &= \mathrm{gross}-\mathrm{fees} \\
r &= \mathrm{net}/C_{\mathrm{entry}}
\end{aligned}
\]

Compound:

\[
R = \prod_k (1+r_k) - 1
\]

**Example.** Entry 100, exit 102, fees 10 bps, slippage 5 bps:

\(s=0.0005\), \(f=0.001\)

\(P_{in}=100.05\), \(P_{out}=101.949\), gross≈1.899, fees≈0.202, net≈1.697, \(r\approx1.70\%\).

## Baselines

**Buy and hold:** one long from first to last close of the **eval window**, same cost model, \(r=\mathrm{net}/C_0\).

**Random:** 200 trials (`n_trials=200`, `seed=42`), each placing **exactly `k` entries** where `k = count_trades(model_mask, horizon)` — same frequency as the model. Average \(R\).

**Gate:**

```text
published = (model_net > buy_hold) and (model_net > random)
```

**Example from tests:** a perfect classifier on an alternating series publishes; a constant p=0.1 model never clears 0.55, takes 0 trades, \(R=0\), loses to positive buy-and-hold, **unpublished**. Inference worker then emits nothing.

## Brier / AUC / F1 / ROC

**Not computed** in `train_model`. Don’t claim them unless you add them.

---

# 13. Inference in production

## Serialization

`pickle.dump({"model": final_model, "calibrator": calibrator})`  
Path: `/data/ml_models/{instrument_group}_{version}.pkl`  
Refuse overwrite unless `overwrite=True`.

Comment mentions “Fly volume”; HF README says disk is **ephemeral**. **Ops conflict:** models can vanish on Space restart.

## Loading

`pickle.load` in the worker. **Security:** pickle executes bytecode — only load artifacts you trained.

## Serving path

1. `instrument_group_for("BTC/USDT")` → `"crypto_majors"`; other `*/USDT` → `"crypto_alts"`; else `"nse_equities"`.
2. All **published** models in that group get a job (a symbol can trigger multiple versions if several rows are published).
3. `build_features` **must match training** (same windows). Regime omitted.
4. Missing `metrics["threshold"]` → **ValueError** (fail loud, don’t silently use 0.55).
5. Redis key `signal_dedup:ml:{model_id}:{instrument_id}:{bar_ts}` SET NX, TTL `DEDUP_TTL_SECONDS`.
6. Signal `confidence=prob_up`, `meta.model_id`, baseline snapshot.

## API

- `GET /ml/models` — **no auth dependency** in handler (**Verified**).
- `GET /ml/models/{id}` — metrics for UI.
- **No POST /train.**

## Latency / hardware

LightGBM predict on 1×7 is microseconds. Feature build on 250 rows is cheap pandas. FinBERT on CPU is the slow DL piece (news cron). BGE encode is offloaded with `asyncio.to_thread` so the chat event loop doesn’t block.

**GPU:** FinBERT `device=-1` **forces CPU**. No CUDA API in app code.

## Scaling to 1M requests

This design is **bar-close jobs**, not “1M HTTP predicts/sec.” Scale story: more symbols × more published models = more arq jobs; LightGBM is not the bottleneck; **ingest and DB** are. Don’t invent a GPU cluster.

---

# 14. Hyperparameters

| Name | Value | Controls | If ↑ | If ↓ | Tune how |
| --- | --- | --- | --- | --- | --- |
| `n_estimators` | 100 | boosting rounds | more fit, slower, overfit risk | underfit | CV economic gate, not just acc |
| `num_leaves` | 15 | tree complexity | deeper interactions, overfit | more bias | keep small on noisy bars |
| `learning_rate` | 0.05 | shrinkage | faster fit, unstable | need more trees | paired with n_estimators |
| `random_state` | 42 | reproducibility | — | — | don’t “tune” |
| `horizon` | caller (tests use 1) | label & hold period | harder problem, more purge | noisier labels | must match serve holding |
| `n_splits` | caller (tests 3) | CV folds | more compute, less train in early folds | noisier gate | need enough samples |
| `test_size` | caller (tests 8) | test length | more honest, needs more n | noisy acc | |
| `purge` | caller; **must ≥ horizon** | embargo | less train data | **leakage** | never < horizon |
| `threshold` | 0.55 default | trade frequency | fewer trades, higher precision hope | more trades, more fees | stored in metrics |
| `fees_bps` / `slippage_bps` | caller (tests 10 / 5) | cost drag | harder to publish | optimistic gate | use realistic live fees |
| `ML_WINDOW_BARS` | 250 | serve history | more warmup safety | might starve RSI | ≥ ~20+14 |
| `MIN_ML_BARS` | 30 | skip inference | — | — | |
| FinBERT `batch_size` | 16 | news throughput | more RAM | slower | |
| FinBERT `device` | -1 | CPU | — | — | GPU would be `0` if you added it |
| BGE dim | 384 | vector size | — | — | must match `VECTOR(384)` |
| chunk `max_tokens` | 200 **words** | chunk size | more context, diluted embedding | too small | name says tokens, code counts **words** |
| RAG `k` | 4 | retrieved chunks | more noise to LLM | miss facts | |

**Not present:** dropout, batch size (trees), hidden size, epochs, Adam β, warmup schedule, weight decay kwargs.

---

# 15. Array / tensor shape walkthrough

There is no `(batch, seq, hidden)` in the trading model.

## LightGBM

```text
candles DataFrame
  shape (T, 5)     columns o,h,l,c,v   T ≈ 250 at serve, larger at train

build_features
  shape (T - warmup, 7 + regime cols + feature_ts)
  warmup ≈ 20 bars (volume/VWAP window)

join labels
  shape (n, ...)   n < T  (lost warmup + last `horizon` bars)

X = FEATURE_COLUMNS
  shape (n, 7)

y
  shape (n,)       values 0.0 / 1.0

predict_proba(X_test)
  shape (n_test, 2)

raw_test[:, 1]
  shape (n_test,)

isotonic.predict
  shape (n_eval,)

serve latest_row
  shape (1, 7)
predict_proba
  shape (1, 2)
prob_up
  scalar
```

## BGE

```text
texts: list of N strings
encode → (N, 384) float32  (typical)
normalize_embeddings=True → each row L2 norm 1
tolist → list[list[float]] length 384
Postgres VECTOR(384)

query: (384,)
cosine_distance sort
```

## FinBERT

**Reasonable inference** of BERT-base-uncased style (FinBERT is BERT-based):

```text
batch of headlines B=16
tokens: (B, L)      L ≤ 512
hidden: (B, L, 768)  if base
logits: (B, 3)       positive / negative / neutral  (typical FinBERT)
softmax → scores
we use P(pos) - P(neg)  → (B,)
```

This repo never prints those shapes; it uses `pipeline(..., top_k=None)` and reads labels.

---

# 16. Deep learning system 1 — FinBERT sentiment

## Why it exists

News ingest stores a numeric `sentiment` for the dashboard and `get_news` chat tool.

## Problem

Classify a **headline** into signed sentiment, not trade direction.

## Input / output

- In: `list[str]` titles  
- Out: `list[float]` in roughly [-1, 1]

\[
s = P(\text{positive}) - P(\text{negative})
\]

Neutral probability is ignored in the difference (it still occupies mass so |s| < 1 often).

**Example.** Title: “Fed unexpected rate cut.” Suppose P(pos)=0.71, P(neg)=0.09, P(neu)=0.20 → s=0.62.

## Architecture (pretrained BERT classifier)

```text
tokens + [CLS] ... [SEP]
        ↓
BERT encoder (self-attention × N layers)
        ↓
[CLS] hidden vector
        ↓
linear classification head
        ↓
softmax over {positive, negative, neutral}
```

**We do not train this.** `transformers.pipeline("text-classification", model="ProsusAI/finbert", device=-1, batch_size=16, top_k=None)`.

Lazy import so unit tests don’t load torch.

## Mathematics you should be able to sketch

**Self-attention (one head):** for query/key/value matrices from token embeddings,

\[
\mathrm{Attention}(Q,K,V)=\mathrm{softmax}\Big(\frac{QK^\top}{\sqrt{d_k}}\Big)V
\]

**Softmax:**

\[
\mathrm{softmax}(z)_i = \frac{e^{z_i}}{\sum_j e^{z_j}}
\]

**GELU** is BERT’s FFN activation (library internals). **Dying ReLU** is irrelevant unless you train your own net.

## Training / optimizer / backprop

Happened at Prosus / original authors. Typical BERT fine-tune: Adam, lr ~2e-5, cross-entropy. **Not in this repo.**

## Limitations

- Headlines ≠ full articles  
- Domain shift (crypto Twitter vs FinBERT’s news)  
- CPU latency on cron  
- No calibration of s into trading features (sentiment is **not** an LightGBM input)

## Interview

“Did you fine-tune FinBERT on your RSS?” — **No. Verified: inference only.**

---

# 17. Deep learning system 2 — BGE embeddings + RAG

## Why

Chat tool `search_kb` must retrieve educational markdown (position sizing, ORB, disclaimers) by **meaning**.

## Pipeline

1. `chunk_markdown` — paragraphs packed until **word** count > 200 (`max_tokens` is a misnomer).
2. `SentenceTransformer("BAAI/bge-small-en").encode(..., normalize_embeddings=True)`
3. Store in `kb_chunks`
4. Query: embed → `order_by(embedding.cosine_distance(vector)).limit(k)`

## Mathematics

If vectors are L2-normalized, cosine similarity = dot product:

\[
\cos(q,d) = q^\top d,\quad \|q\|=\|d\|=1
\]

pgvector `cosine_distance` is \(1-\cos\) (**typical**; don’t swear to the SQL operator without docs, but **ordering by smaller distance = nearer** is what `order_by` does).

**Example.** Query “what is a stop loss?” should rank `stop_loss_and_risk.md` chunks above `grid_range.md`.

## Architecture (sentence-transformers)

Transformer encoder → pooling → 384-d vector. **Frozen.**

`embed_texts_async` uses `asyncio.to_thread` so encode doesn’t block FastAPI.

## Why 384

`KBChunk.embedding = Vector(384)` **must** match the model. Changing to `bge-base` (768) without a migration would break.

## Limitations

- Small curated KB, likely no ANN index in migration 0001 (**Unknown** if later indexes exist; 0001 did not create IVFFlat)
- Chunking by words can split mid-concept
- Retrieved text is wrapped as untrusted `TOOL_DATA` in the chat orchestrator (prompt-injection), which is **ML-adjacent safety**, not a model layer

---

# 18. Tools and libraries

Only what is real.

### LightGBM

`lgb.LGBMClassifier(...).fit / predict_proba / feature_importances_`

sklearn-compatible API. Histogram boosting internally.

### scikit-learn

`IsotonicRegression` only in `app/ml/calibration.py`. Not `train_test_split`, not `StandardScaler`, not `Pipeline`.

### pandas

OHLCV frames, `pct_change`, `rolling`, `join`, `iloc`.

### NumPy

Walk-forward index arrays, OOF buffers, random baseline `default_rng`, `simulate_directional_returns` on `ndarray`.

### pickle + pathlib

Artifact I/O. Not `joblib` (though sklearn often uses it). Not ONNX.

### transformers + torch (transitive)

FinBERT pipeline. **No** `torch.nn` in `app/`.

### sentence-transformers + torch

BGE encode.

### pgvector

`Vector(384)`, cosine distance in SQLAlchemy.

### pytest

Synthetic candles + `_PerfectClassifier` / `_NullClassifier` doubles so CI does not need a real LightGBM edge or GPU.

### Frontend

Recharts for feature importance, calibration plot, baseline bars — **visualization of stored metrics**, not training.

### Not used

TensorBoard, MLflow, CUDA APIs, Hugging Face `Trainer`, datasets library, torchvision.

---

# 19. Modelling decisions

| Decision | Chosen | Alternative | Evidence |
| --- | --- | --- | --- |
| Task | Binary direction | Return regression | `y` is 0/1 |
| Model | LightGBM | LSTM / Transformer | `LGBMClassifier`; no `nn.LSTM` |
| Features | 7 TA stats | Raw window tensor | `FEATURE_COLUMNS` |
| Regime in model | **Excluded** | One-hots | comment train/serve skew |
| Labels | Fixed horizon | Triple barrier | `train_model` call |
| Split | Purged expanding WF | Random K-fold | `splitter.py` |
| Probabilities | Isotonic | Raw / Platt | `calibration.py` |
| Publish | Economic gate | Accuracy / always on | `passes_baseline_gate` |
| Threshold | 0.55, persisted | 0.5 | default + metrics assert |
| Side | Long only | Long/short | `direction="long"` |
| Sentiment | Frozen FinBERT | VADER / keyword | `ProsusAI/finbert` |
| RAG | BGE-small 384 | TF-IDF | embedder + pgvector |
| Train job | Library + tests | Live cron | no worker `train_ml` |
| Device | CPU | GPU | `device=-1` |

Where the repo is silent, say so. Example: “Why 0.55 not 0.6?” — **Unknown.** Reasonable: require a bit more than a coin flip after calibration.

---

# 20. Failure modes and debugging

| Failure | Symptom | Cause | Diagnose | Fix |
| --- | --- | --- | --- | --- |
| Leakage | Amazing CV, live trash | purge < horizon; future in features | `assert_*` ; inspect `label_ts` | enforce purge; never center rolling |
| Empty features | No signals | T < warmup; flat volume used to NaN | log `features.empty` | MIN_ML_BARS; z=0 mask (already) |
| Train/serve skew | Live p garbage | extra columns / different RSI | compare `FEATURE_COLUMNS` both paths | keep list in one module (already) |
| Unpublished | Worker no-ops | gate failed | `published` flag | don’t lower costs to cheat; improve features |
| Missing threshold | Job throws | metrics incomplete | error message | `train_result_metrics()` |
| Artifact gone | pickle FileNotFound | HF ephemeral disk | logs | bake into image / object store |
| Group mismatch | BTC never scored | trained `btc` vs `crypto_majors` | `instrument_group_for` | use the convention |
| Constant proba | calibrator None | model collapsed | unique raw values | more data / weaker regularization? |
| Overfit trees | fold acc >> later live | 100 trees on tiny n | compare folds over time | fewer leaves, more purge |
| Underfit | never beats BH | no edge | gate false | accept “no model” |
| Class imbalance | always down hours | crypto dump | check `y.mean()` | class weight (not implemented) |
| Distribution shift | 2022 model in 2026 | regime change | live vs train vol | retrain (no cron today) |
| Sentiment NaNs | news sentiment null | pipeline fail | worker logs | keep lazy import; CPU OOM |
| RAG junk | wrong chunks | k too big / bad chunk | inspect `search_kb` | smaller k, better chunks |
| Shape error | LightGBM feature name mismatch | DataFrame vs ndarray | serve uses named columns | keep DataFrame |
| Pickle / version | load error | lightgbm upgraded | pip freeze vs train env | `uv.lock` |
| Duplicate signals | two rows one bar | redis down | unique? signals table has **no** unique like scan_hits | Redis NX; add DB unique if needed |
| CUDA | N/A | we pin CPU | — | don’t “fix CUDA” unless you change device |
| `loss.backward` NaN | N/A | not our loop | — | |

## If the model isn’t learning (tests / local train)

1. **Labels:** `y.mean()` not 0 or 1 for all rows.  
2. **Volume varies** — tests document constant volume → all `volume_z` NaN → zero rows.  
3. **horizon / purge / n_samples** — `ValueError` fold exceeds n.  
4. **Classifier factory** — tests inject doubles; production uses LightGBM.  
5. **Threshold vs raw p** — null model p=0.1 never trades.  
6. **Don’t debug autograd.**

## If live ML is silent

1. Ingest 1h bars?  
2. `MLModel.published`?  
3. `instrument_group_for(symbol)` matches row?  
4. ≥30 1h candles?  
5. `p >= threshold`?  
6. Redis already claimed dedup?  
7. Worker running?

---

# 21. ML/DL interview questions and answers

### Basic

**Q: What problem is your model solving?**  
**Short:** Binary classification: will the close in `h` bars be higher than now? If calibrated probability ≥ threshold and the model beat baselines after fees, we emit a long-only educational signal.  
**Deeper:** Separate systems: FinBERT for news, BGE for RAG. We didn’t train those.

**Q: Is this deep learning?**  
**Short:** The signal model is gradient boosting. DL is used as frozen Hugging Face models for text.

### Intermediate

**Q: Why LightGBM not LSTM?**  
**Short:** Inputs are 7 scalars, not a long sequence we want to learn from scratch; sample is small; we need CPU, leakage control, and a publish gate. LSTM would add sequence leakage risk and ops cost without evidence in this repo that it wins.  
**Deeper:** We even refused regime one-hots because serve couldn’t reproduce them — that same discipline argues against a hidden-state model we can’t align.

**Q: Why 7 features?**  
**Short:** Returns at 1/3/5, short vol, RSI, volume surprise, distance to VWAP. Interactions come from trees.  
**Deeper:** Adding raw close would leak scale (BTC 60000 vs a 3-rupee stock); returns are comparable.

### Mathematical

**Q: What is the loss?**  
**Short:** LightGBM binary log loss (library default; we don’t override). Publishing uses compounded net return, not log loss.

**Q: How does backpropagation work in your trainer?**  
**Short:** It doesn’t. Boosting takes \(\partial L/\partial F = p-y\) and fits a tree. Backprop is inside BERT weights we never update.

**Q: What does the gradient represent?**  
**Short:** For log loss, how much to push the log-odds \(F(x)\) to reduce error. Positive residual \(y-p\) when we under-predicted an up bar.

### Implementation

**Q: Why `iloc[[-1]]` with double brackets?**  
**Short:** Keep a DataFrame (feature names) not a Series. LightGBM sklearn API likes the train schema.

**Q: Why not `model.eval()` / `no_grad()`?**  
**Short:** That’s PyTorch. LightGBM has no dropout/bn train mode. For FinBERT, Hugging Face pipeline handles eval/inference.

**Q: Why pickle?**  
**Short:** Dumps the sklearn/LightGBM object plus isotonic. Fragile across versions; simple. We refuse overwrite so we don’t clobber a gated artifact.

### Tooling

**Q: Why pandas not a Dataset/DataLoader?**  
**Short:** T is hundreds of rows, not millions of images. A DataLoader would be theater.

**Q: What is a tensor here?**  
**Short:** For LightGBM, NumPy/pandas 2D arrays. For BGE, a `(N,384)` embedding matrix produced inside PyTorch then converted `.tolist()`.

### Architecture

**Q: Why `num_leaves=15`?**  
**Short:** Repo doesn’t A/B it. Reasonable: cap interaction order on noisy financial data.

**Q: Why sigmoid (internally)?**  
**Short:** Maps unbounded tree-sum to a probability. We then **recalibrate** because that probability is imperfect.

### Modelling

**Q: Double the learning rate?**  
**Short:** Each tree 2× stronger → likely overfit, wild p, isotonic may clip, gate might fail or spuriously pass on one window.

**Q: What if validation (later OOF) return is worse than train folds’ accuracy?**  
**Short:** Expected: accuracy ≠ PnL; later window may be a different regime. Gate uses later OOF **on purpose**.

### Debugging

**Q: Training loss (log loss) down, economic OOF down?**  
**Short:** Model fits labels but trades after costs lose, or threshold fires at the wrong frequency. Classic “good classifier, bad strategy.”

### Design

**Q: Why not a Transformer on candles?**  
**Short:** Attention over 250 hours with <10k samples is a memorization machine. We already struggle with leakage on tabular CV.

**Q: Why not use sentiment as a LightGBM feature?**  
**Short:** Not implemented. Would need point-in-time news join (no lookahead from a headline published after the bar). That’s a project, not a one-liner.

### Production

**Q: 1 million predict QPS?**  
**Short:** Wrong load model. We predict on 1h closes for ≤25 crypto names. I’d keep jobs; if we did an HTTP predict API, LightGBM on CPU with a tiny vector is enough. I’d worry about Redis/DB, not GPU.

**Q: How do you retrain?**  
**Short:** Call `train_model` offline, insert `ml_models` if `published`, deploy pickle. There is **no** production trainer job. That’s a gap I’d mention first.

---

# 22. Explain this on a whiteboard

## Trading model (draw and talk)

```text
OHLCV bars  →  rolling features (7)  →  y = 1{C_{t+h}>C_t}

      expanding train | purge | test | purge | test | ...

      LightGBM: 100 trees, 15 leaves, lr=0.05
           raw p = P(up)
           isotonic on early OOF
           later OOF: trade if p≥0.55, hold h bars, pay fees
           if R > buy&hold and R > random(k trades): PUBLISH

Live: 1h close → same 7 features on last bar → p̂ → signal or silence
```

Say: “Accuracy is a dashboard number. The model is not allowed to speak unless it beats two costed baselines.”

## FinBERT

```text
headline → tokenizer → BERT → softmax(pos,neg,neu) → p_pos - p_neg → DB
```

Say: “CPU, batch 16, lazy import, not a trading input.”

## RAG

```text
docs → word chunks ≤200 → BGE → unit vector 384
query → same encoder → nearest cosine k=4 → LLM (untrusted data)
```

---

# 23. Unified mental model

```text
Market data
   → pandas features (causal rolling stats)
   → labels from the FUTURE (hence purge)
   → LightGBM additive trees  (fit log loss)
   → raw probabilities
   → isotonic map
   → threshold
   → simulated trades with fees   ← this decides "is ML allowed to exist live"
   → pickle + DB flag
   → on 1h close, same features, one predict
   → optional long signal in the product

Text (parallel universe)
   → frozen transformers
   → sentiment scalar OR 384-d embedding
   → SQL / news table / chat tools
```

How the textbook ideas map:

| Textbook | This project |
| --- | --- |
| Supervised learning | \(y_t\) from future close |
| Features | `FEATURE_COLUMNS` |
| Model | LightGBM ensemble |
| Forward pass | walk trees, sum, sigmoid (lib) |
| Loss | log loss inside `fit` |
| Gradient | boosting residuals, not autograd |
| Optimizer | boosting + shrinkage 0.05 |
| Regularization | small leaves, few trees, purge |
| Validation | purged WF + later-OOF economics |
| Calibration | isotonic |
| Inference | `predict_proba` + threshold |
| DL | FinBERT + BGE, no training loop |
| Application | `signals` / news / RAG |

You should now be able to say: **one tabular boosting system with unusually strict time-series and economic discipline, plus two off-the-shelf text models.**

---

# 24. Recommended study order

| # | Topic | Why | Depth | Revisit |
| --- | --- | --- | --- | --- |
| 1 | What is being predicted | Avoid LSTM fantasy | Can write \(y_t\) | §1, §6 |
| 2 | OHLCV features | Input literacy | Compute ret_1, RSI idea | §5 |
| 3 | Leakage + purge | Hardest interview | Work a 10-bar example | §7 |
| 4 | Trees + boosting | The model | One residual step | §8, §10 |
| 5 | Log loss + sigmoid | p meaning | Hand calc | §9 |
| 6 | Isotonic | Why 0.55 is OK | Split OOF story | §11 |
| 7 | Costs + gate | Why accuracy isn’t king | Compound vs BH | §12 |
| 8 | `train.py` top to bottom | Glue | Trace variables | file |
| 9 | Inference worker + dispatch | Production | 1h only, groups | §13 |
| 10 | FinBERT + BGE | DL honesty | Inference-only | §16–17 |
| 11 | Failure modes | Debug | Volume NaN, pickle | §20 |
| 12 | Answers out loud | Interview | §21–22 | |

---

# 25. Defense checklist

- [ ] I can state the ML problem as binary direction, not “an LSTM predicts price.”
- [ ] I can list the 7 features and why regime is excluded.
- [ ] I can write the fixed-horizon label and say triple-barrier is unused in training.
- [ ] I can explain purge ≥ horizon with a sketch.
- [ ] I can describe LightGBM as 100 shrunk trees, 15 leaves, lr 0.05.
- [ ] I can explain log loss intuitively and admit it’s inside the library.
- [ ] I can explain isotonic OOF split (gate calibrator = shipped calibrator).
- [ ] I can explain the publish gate vs accuracy.
- [ ] I can explain non-overlapping horizon exits and why mapping to full `close` matters.
- [ ] I can walk live inference: 1h, 250 bars, group names, threshold assert, Redis dedup.
- [ ] I can say there is no train API / no GPU training loop.
- [ ] I can explain FinBERT `P(pos)-P(neg)` on CPU.
- [ ] I can explain BGE 384, cosine, word chunks of 200.
- [ ] I can name pickle / ephemeral disk as a deploy risk.
- [ ] I can answer “why not Transformer?” without buzzwords.
- [ ] I can debug “no live ML signals” from ingest → published flag → p.

---

# 26. Things I must learn

## MUST KNOW

> **Learn: Time-series leakage**  
> Be able to explain why `feature_ts < label_ts`, why `purge >= horizon`, and what `assert_no_cross_fold_leakage` blocks. Draw expanding train / gap / test.

> **Learn: Binary classification labels on prices**  
> Write \(y=\mathbf{1}\{C_{t+h}>C_t\}\). Say what that ignores (magnitude, stops).

> **Learn: Gradient boosting vs neural nets**  
> Describe additive trees, shrinkage, `n_estimators` as rounds. Explicitly contrast with `loss.backward()`.

> **Learn: The 7 features**  
> Formula-level for return, RSI idea, z-score, VWAP distance, and the flat-volume NaN trap.

> **Learn: Economic publish gate**  
> Compounded net return, buy-and-hold, frequency-matched random, `published` flag.

> **Learn: Serve contract**  
> `FEATURE_COLUMNS`, 1h only, `metrics["threshold"]` required, `instrument_group_for`.

## SHOULD KNOW

> **Learn: Isotonic regression**  
> Nondecreasing map from raw p to [0,1]; why they fit on early OOF only.

> **Learn: Log loss**  
> Formula, why it scores probabilities, tiny numerical example.

> **Learn: Transaction costs in bps**  
> Effective entry/exit and why a 55% accurate model can still lose money.

> **Learn: Frozen transformers**  
> FinBERT pipeline; BGE `encode`; cosine retrieval; CPU; lazy import.

> **Learn: Pickle artifacts**  
> Path convention, overwrite guard, version fragility, HF disk.

## DEEP DIVE IF ASKED

> **Learn: LightGBM histogram / leaf-wise growth**  
> Enough to say why `num_leaves` not `max_depth` is the native knob.

> **Learn: Triple-barrier labeling (Lopez de Prado)**  
> You can implement it (the function exists) and explain why the trainer still uses fixed horizon.

> **Learn: BERT attention formula**  
> One-head attention + softmax; you are not expected to derive multi-head from memory unless they pivot to NLP.

> **Learn: Class imbalance and sample weights**  
> Not in code; discuss as an improvement.

> **Learn: Combining news embeddings with tabular features**  
> Point-in-time join; leakage if news is timestamped wrong.

---

# Appendix — Code map

| Path | Role |
| --- | --- |
| `market-assistant/backend/app/ml/features.py` | Feature engineering |
| `market-assistant/backend/app/ml/labels.py` | Fixed horizon + unused triple barrier |
| `market-assistant/backend/app/ml/splitter.py` | Purged walk-forward |
| `market-assistant/backend/app/ml/train.py` | Train, gate, pickle |
| `market-assistant/backend/app/ml/calibration.py` | Isotonic |
| `market-assistant/backend/app/ml/inference.py` | `predict_prob_up`, threshold check |
| `market-assistant/backend/app/ml/evaluate.py` | Costed simulation |
| `market-assistant/backend/app/ml/baseline.py` | BH, random, gate |
| `market-assistant/backend/app/ml/registry.py` | Save/load pickle |
| `market-assistant/backend/app/ml/grouping.py` | Symbol → group |
| `market-assistant/backend/app/backtest/leakage.py` | Leakage asserts |
| `market-assistant/backend/app/backtest/costs.py` | Fees/slippage |
| `market-assistant/backend/app/workers/ml_inference_worker.py` | Live predict |
| `market-assistant/backend/app/ingest/dispatch.py` | When to enqueue ML |
| `market-assistant/backend/app/ingest/sentiment.py` | FinBERT |
| `market-assistant/backend/app/chat/kb/embedder.py` | BGE |
| `market-assistant/backend/app/chat/kb/chunker.py` | Chunking |
| `market-assistant/backend/app/chat/kb/seed.py` | Seed embeddings |
| `market-assistant/backend/app/chat/tools/kb_tools.py` | Vector search |
| `market-assistant/backend/app/models/ml_model.py` | Registry ORM |
| `market-assistant/backend/app/api/ml.py` | GET models |
| `market-assistant/frontend/src/pages/ML.tsx` | Empty list state |
| `market-assistant/frontend/src/pages/MLModels.tsx` | Metrics UI |
| `market-assistant/backend/tests/integration/test_ml_train_job.py` | Gate tests |

---

# Closing honesty

**Production-ready ML engineering:** leakage tests, serve/train column parity, threshold persistence, economic gate, CPU-friendly model.

**Not production-ready ML ops:** no training service, no scheduled retrain, pickle on possibly ephemeral disk, `/ml` list page still an empty-state stub, unauthenticated model GET, sentiment not in the classifier.

If you remember only one defense line:

> We treated financial ML as a **leakage and costs problem** first, and a **model architecture problem** second — that’s why the live model is a small LightGBM with a publish gate, not a custom neural net.
