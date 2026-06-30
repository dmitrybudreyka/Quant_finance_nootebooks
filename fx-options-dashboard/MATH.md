# Math Behind the FX Options Pricing Mechanism

This dashboard prices European EUR/USD options with the Garman-Kohlhagen model, which is the Black-Scholes framework adapted to foreign exchange. The key FX-specific idea is that the option payoff is paid in the domestic currency, while the spot asset is a foreign currency that earns the foreign risk-free rate.

For EUR/USD in this project:

- `S` is the EUR/USD spot rate, quoted in USD per 1 EUR.
- `K` is the strike, also quoted in USD per 1 EUR.
- `T` is time to maturity in years.
- `rd` is the domestic risk-free rate. For EUR/USD, this is the USD rate.
- `rf` is the foreign risk-free rate. For EUR/USD, this is the EUR rate.
- `sigma` is the implied volatility from the volatility surface.
- `N(x)` is the standard normal cumulative distribution function.
- `n(x)` is the standard normal probability density function.

## Model Assumptions

Garman-Kohlhagen assumes the FX spot rate follows a lognormal process under the domestic risk-neutral measure:

```text
dS / S = (rd - rf) dt + sigma dW
```

The drift is `rd - rf`, not simply `rd`, because holding the foreign currency earns the foreign interest rate. Economically, foreign currency behaves like a dividend-paying asset where the "dividend yield" is `rf`.

The dashboard uses this model for European options, so exercise happens only at maturity. It does not model early exercise, barriers, smile dynamics, stochastic volatility, or counterparty/funding adjustments.

## d1 and d2

The pricing formulas are built around two normalized terms:

```text
d1 = [ln(S / K) + (rd - rf + 0.5 * sigma^2) * T] / [sigma * sqrt(T)]

d2 = d1 - sigma * sqrt(T)
```

Intuitively:

- `d1` measures how far the forward-adjusted spot is from the strike in volatility units.
- `d2` is the same threshold adjusted for the uncertainty accumulated over the option's life.
- `N(d2)` can be read as a risk-neutral exercise probability for a call in the Black-Scholes-style framework.
- `N(d1)` appears in the option's spot sensitivity and discounted asset exposure.

In code, these terms are calculated in `src/utils.py` by `calculate_d1_d2`.

## Pricing Formula

The model discounts the expected option payoff back to today. For a call option:

```text
C = S * exp(-rf * T) * N(d1) - K * exp(-rd * T) * N(d2)
```

For a put option:

```text
P = K * exp(-rd * T) * N(-d2) - S * exp(-rf * T) * N(-d1)
```

The two discount factors have different meanings:

- `exp(-rd * T)` discounts USD cash paid or received at maturity.
- `exp(-rf * T)` discounts the foreign-currency spot exposure, because EUR earns the foreign rate.

This is implemented in `src/garman_kohlhagen.py` by `price_fx_option`.

## Forward Interpretation

The no-arbitrage FX forward rate is:

```text
F = S * exp((rd - rf) * T)
```

The call price can also be understood as a discounted option on the forward:

```text
C = exp(-rd * T) * [F * N(d1) - K * N(d2)]
```

This is algebraically equivalent to the Garman-Kohlhagen call formula because:

```text
exp(-rd * T) * F = S * exp(-rf * T)
```

This view is useful on an FX desk because forwards are central market instruments.

## Put-Call Parity

For European FX options, call and put prices must satisfy:

```text
C - P = S * exp(-rf * T) - K * exp(-rd * T)
```

The right-hand side is the present value of receiving foreign currency exposure and paying the domestic strike. The test suite checks this relationship in `tests/test_garman_kohlhagen.py`.

## Intrinsic Value Edge Case

If `T = 0` or `sigma = 0`, the implementation returns intrinsic value:

```text
Call intrinsic = max(S - K, 0)
Put intrinsic  = max(K - S, 0)
```

This avoids dividing by zero in `d1` and `d2`. In a full production pricer, zero-volatility but positive-maturity valuation could also be treated through deterministic forwards; this project keeps the edge case simple and explicit.

## Implied Volatility Surface

The model needs `sigma`, but in real markets volatility is not constant across strikes and maturities. The dashboard loads a grid of implied volatilities:

```text
sigma = sigma(K, T)
```

The project stores a synthetic EUR/USD surface in `data/sample_vol_surface.csv`. The `VolatilitySurface` class:

1. Loads the rectangular grid of maturities, strikes, and implied volatilities.
2. Pivots it into a maturity-by-strike matrix.
3. Uses regular grid interpolation to estimate volatility for the selected strike and maturity.

The interpolated volatility is then passed into the Garman-Kohlhagen formula. This keeps market data logic separate from pricing logic.

## Greeks

Greeks measure sensitivities of the option price to market inputs. They are implemented analytically in `src/greeks.py`.

### Delta

Delta is sensitivity to spot:

```text
Call delta = exp(-rf * T) * N(d1)
Put delta  = -exp(-rf * T) * N(-d1)
```

For EUR/USD, delta is EUR exposure per 1 EUR of option notional. A call has positive delta; a put has negative delta.

### Gamma

Gamma is sensitivity of delta to spot:

```text
Gamma = exp(-rf * T) * n(d1) / [S * sigma * sqrt(T)]
```

Gamma is positive for both calls and puts in this model. High gamma means delta changes quickly when spot moves.

### Vega

Vega is sensitivity to implied volatility:

```text
Vega = S * exp(-rf * T) * n(d1) * sqrt(T)
```

The code reports vega for a volatility change of `1.00` in decimal terms. To estimate value change for a 1 percentage point vol move, multiply vega by `0.01`.

### Theta

Theta is sensitivity to time passing. For a call:

```text
Theta_call =
    -S * exp(-rf * T) * n(d1) * sigma / [2 * sqrt(T)]
    + rf * S * exp(-rf * T) * N(d1)
    - rd * K * exp(-rd * T) * N(d2)
```

For a put:

```text
Theta_put =
    -S * exp(-rf * T) * n(d1) * sigma / [2 * sqrt(T)]
    - rf * S * exp(-rf * T) * N(-d1)
    + rd * K * exp(-rd * T) * N(-d2)
```

Theta can be negative or positive depending on rates, moneyness, and option type. The dashboard reports theta per year.

### Rho

The model has two rate sensitivities because FX uses both domestic and foreign rates.

Domestic rho:

```text
Call domestic rho =  K * T * exp(-rd * T) * N(d2)
Put domestic rho  = -K * T * exp(-rd * T) * N(-d2)
```

Foreign rho:

```text
Call foreign rho = -T * S * exp(-rf * T) * N(d1)
Put foreign rho  =  T * S * exp(-rf * T) * N(-d1)
```

For EUR/USD, domestic rho measures sensitivity to USD rates, and foreign rho measures sensitivity to EUR rates.

## Scenario Analysis

The scenario engine reprices the option after changing one or more inputs:

```text
P&L = scenario option price - base option price
```

The dashboard includes spot shocks, volatility shocks, parallel rate shocks, combined spot/vol shocks, and a one-month time decay scenario. Each scenario recomputes both price and Greeks instead of only approximating P&L from the base Greeks.

This is implemented in `src/scenario_analysis.py`.

## Delta Hedging Logic

The hedge recommendation uses option delta and notional:

```text
Portfolio delta = option delta * notional
```

If portfolio delta is positive, the position benefits from EUR/USD rising, so the hedge is to sell EUR/USD forward in approximately that EUR amount. If portfolio delta is negative, the hedge is to buy EUR/USD forward.

This is a simple first-order hedge. It neutralizes spot exposure locally, but it does not remove gamma, vega, theta, or rate risk. As spot and volatility move, delta changes, so the hedge would need to be rebalanced.

## End-to-End Pricing Flow

The dashboard pricing workflow is:

1. User selects spot, strike, maturity, rates, option type, and notional.
2. The volatility surface interpolates `sigma(K, T)`.
3. The pricer computes `d1`, `d2`, discount factors, and option price.
4. Analytical Greeks are calculated from the same inputs.
5. Scenario analysis reprices the option under stressed inputs.
6. Delta is multiplied by notional to produce a simple forward hedge recommendation.

The result is a compact FX options analytics workflow: market volatility in, model value and risk measures out.
