"""
ProbabilisticDataFrame
======================
Automatic uncertainty propagation for DataFrame/Series calculations.

Two methods are implemented:

* **Monte Carlo** (GUM Supplement 1, JCGM 101:2008): input quantities are
  sampled from their probability distributions and fed through the model
  function. The output distribution is characterised by its mean, standard
  deviation and quantile-based coverage interval.

* **Linear** (GUM §5.1.2, JCGM 100:2008): the combined standard uncertainty
  is obtained from the law of propagation of uncertainty, where sensitivity
  coefficients are evaluated by central finite differences.  Cross-covariance
  contributions are included when a correlation matrix is supplied.

Supported input distributions (MC only)
----------------------------------------
``'normal'``     – standard uncertainty equals 1σ of the Gaussian.
``'uniform'``    – symmetric rectangular PDF; standard uncertainty = h/√3,
                   where h is the half-width.
``'triangular'`` – symmetric triangular PDF; standard uncertainty = h/√6.

References
----------
JCGM 100:2008 – Evaluation of measurement data — Guide to the expression
of uncertainty in measurement (GUM).
JCGM 101:2008 – Supplement 1 to the GUM — Propagation of distributions
using a Monte Carlo method.
"""

import math
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm as _norm


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_SUPPORTED_DISTRIBUTIONS = ("normal", "uniform", "triangular")


# ---------------------------------------------------------------------------
# Class
# ---------------------------------------------------------------------------


class ProbabilisticDataFrame:
    """Automatic uncertainty propagation for DataFrame/Series calculations.

    Central values are stored in *df* and their standard uncertainties in
    *udf*.  After calling :meth:`propagate`, the result column is appended
    to both *df* and *udf*, and the coverage interval is stored internally
    and accessible via :meth:`coverage_interval`.

    Parameters
    ----------
    df : pd.DataFrame or pd.Series
        Measured central values.
    udf : pd.DataFrame or pd.Series
        Standard uncertainties, same shape and labels as *df*.
    """

    def __init__(
        self,
        df: pd.DataFrame | pd.Series,
        udf: pd.DataFrame | pd.Series,
    ) -> None:
        self.df = df
        self.udf = udf
        self._coverage_intervals: dict = {}
        self._check()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def coverage_interval(self, output_name: str):
        """Return the coverage interval ``(lower, upper)`` for *output_name*.

        The bounds are computed during :meth:`propagate` at the significance
        level *alpha* passed to that call.

        * For ``'MC'``    : quantile-based bounds (distribution-free).
        * For ``'linear'``: symmetric Gaussian bounds ``y ± k·u_c``,
          where ``k = z_{1-α/2}`` (large degrees-of-freedom approximation).

        Returns
        -------
        tuple
            ``(lower, upper)`` — scalars for Series inputs, pd.Series for
            DataFrame inputs.

        Raises
        ------
        KeyError
            If :meth:`propagate` has not been called for *output_name*.
        """
        if output_name not in self._coverage_intervals:
            raise KeyError(
                f"No coverage interval stored for '{output_name}'. "
                "Run propagate() first."
            )
        return self._coverage_intervals[output_name]

    @staticmethod
    def n_samples(delta_target: float = 0.01) -> int:
        """Minimum MC sample count following GUM Supplement 1 §7.9.

        The relative standard uncertainty on the estimated output standard
        deviation satisfies::

            u_rel(s) ≈ 1 / sqrt(2 · (M − 1))

        Setting ``u_rel(s) ≤ delta_target`` yields::

            M ≥ 1 / (2 · delta_target²) + 1

        A hard minimum of 10 000 is enforced per GUM-S1 §7.9.

        Parameters
        ----------
        delta_target : float
            Maximum acceptable relative uncertainty on the output standard
            deviation estimate (default 0.01 → 1 %).

        Returns
        -------
        int
        """
        if delta_target <= 0.0:
            raise ValueError("delta_target must be strictly positive.")
        nu_min = math.ceil(1.0 / (2.0 * delta_target ** 2))
        return max(nu_min + 1, 10_000)

    def propagate(
        self,
        xk: list[str],
        model_fn,
        output_name: str,
        alpha: float = 0.05,
        method: str = "MC",
        distributions: list[str] | None = None,
        correlation: np.ndarray | None = None,
        seed: int | None = None,
        delta_target: float = 0.01,
        step_size: float = 1e-6,
    ) -> None:
        """Evaluate *model_fn* on the input columns and propagate uncertainties.

        Results are written in-place to ``self.df[output_name]`` (central
        value) and ``self.udf[output_name]`` (standard uncertainty).  The
        coverage interval is stored and accessible via
        :meth:`coverage_interval`.

        Parameters
        ----------
        xk : list of str
            Column names of the input quantities in *df* / *udf*.
        model_fn : callable
            ``f(data: dict[str, array-like]) -> array-like``

            Receives a ``dict`` mapping each name in *xk* to its values:

            * ``'linear'`` — values are ``pd.Series`` (or Python scalars
              when *df* is a ``pd.Series``).
            * ``'MC'``     — values are 2-D ``ndarray`` of shape
              ``(n_pop, n_mc)``, or 1-D ``(n_mc,)`` for Series inputs.

            The function must support NumPy broadcasting so that it works
            on both cases without modification.

            Example::

                def my_model(data):
                    return data["P"] / (R * data["T"])

        output_name : str
            Name under which the result is stored in *df* and *udf*.
        alpha : float
            Significance level for the coverage interval (default 0.05
            → 95 % coverage probability).
        method : {'MC', 'linear'}
            ``'MC'``      Monte Carlo simulation (GUM Supplement 1).
            ``'linear'``  First-order Taylor expansion (GUM §5.1.2).
        distributions : list of str, optional
            PDF type for each variable, same order as *xk*.  Supported:
            ``'normal'``, ``'uniform'``, ``'triangular'`` (default: all
            ``'normal'``).  Ignored when *correlation* is provided.
        correlation : (nvar, nvar) array-like, optional
            **Correlation** matrix of the input quantities (dimensionless,
            diagonal = 1, off-diagonal in [-1, 1]).  The actual per-row
            covariance is reconstructed internally as::

                cov(Xi, Xj)[row] = R[i,j] · u(Xi)[row] · u(Xj)[row]

            This guarantees the covariance structure is always consistent
            with the per-row uncertainties stored in *udf*, even when those
            uncertainties vary across rows.  When provided:

            * ``'MC'``     — per-row multivariate normal sampling via a
              single Cholesky decomposition of R.
            * ``'linear'`` — per-row cross-covariance terms are added to
              the combined variance per GUM §5.2.2.
        seed : int, optional
            Seed for the random number generator (``'MC'`` only).
        delta_target : float
            Target relative accuracy on the output std estimate; controls
            the number of MC samples (default 0.01, ``'MC'`` only).
        step_size : float
            Relative finite-difference step for sensitivity coefficients
            (``'linear'`` only, default 1e-6).
        """
        if method == "MC":
            self._propagate_mc(
                xk, model_fn, output_name, alpha,
                distributions, correlation, seed, delta_target,
            )
        elif method == "linear":
            self._propagate_linear(
                xk, model_fn, output_name, alpha, correlation, step_size,
            )
        else:
            raise ValueError(
                f"Unknown method '{method}'. Choose 'MC' or 'linear'."
            )

    # ------------------------------------------------------------------
    # Private — validation
    # ------------------------------------------------------------------

    def _check(self) -> None:
        """Validate shape and label alignment of *df* and *udf*."""
        if self.df.shape != self.udf.shape:
            warnings.warn(
                f"df and udf have different shapes: "
                f"df={self.df.shape}, udf={self.udf.shape}.",
                stacklevel=3,
            )
        if isinstance(self.df, pd.DataFrame):
            if not self.df.columns.equals(self.udf.columns):
                warnings.warn(
                    "df and udf have different column names:\n"
                    f"  df.columns  = {list(self.df.columns)}\n"
                    f"  udf.columns = {list(self.udf.columns)}",
                    stacklevel=3,
                )
        elif isinstance(self.df, pd.Series):
            if not self.df.index.equals(self.udf.index):
                warnings.warn(
                    "df and udf have different index labels:\n"
                    f"  df.index  = {list(self.df.index)}\n"
                    f"  udf.index = {list(self.udf.index)}",
                    stacklevel=3,
                )

    def _validate_inputs(self, xk: list[str]) -> None:
        """Check that all columns exist and that all uncertainties are > 0."""
        for col in xk:
            if col not in self.df:
                raise KeyError(f"Column '{col}' not found in df.")
            if col not in self.udf:
                raise KeyError(f"Column '{col}' not found in udf.")
            u_vals = np.asarray(self.udf[col], dtype=float).ravel()
            if np.any(u_vals <= 0.0):
                raise ValueError(
                    f"Non-positive uncertainty detected in udf['{col}']. "
                    "Standard uncertainties must be strictly positive."
                )

    # ------------------------------------------------------------------
    # Private — Monte Carlo (GUM Supplement 1)
    # ------------------------------------------------------------------

    def _propagate_mc(
        self,
        xk: list[str],
        model_fn,
        output_name: str,
        alpha: float,
        distributions: list[str] | None,
        correlation: np.ndarray | None,
        seed: int | None,
        delta_target: float,
    ) -> None:
        """Monte Carlo propagation — GUM Supplement 1 (JCGM 101:2008)."""
        self._validate_inputs(xk)

        nvar = len(xk)
        is_series = isinstance(self.df, pd.Series)
        n_pop = 1 if is_series else len(self.df)
        n_mc = self.n_samples(delta_target)

        # Resolve and validate distribution list
        if distributions is None:
            distributions = ["normal"] * nvar
        if len(distributions) != nvar:
            raise ValueError(
                f"distributions has {len(distributions)} entries "
                f"but xk has {nvar}."
            )
        for d in distributions:
            if d not in _SUPPORTED_DISTRIBUTIONS:
                raise ValueError(
                    f"Unknown distribution '{d}'. "
                    f"Supported: {_SUPPORTED_DISTRIBUTIONS}."
                )

        rng = np.random.default_rng(seed)

        # --- Draw input samples ---
        # Each element of `samples`: shape (n_pop, n_mc) or (n_mc,)
        if correlation is not None:
            if any(d != "normal" for d in distributions):
                warnings.warn(
                    "Non-normal distributions are ignored when a correlation "
                    "matrix is provided; multivariate normal sampling is used.",
                    stacklevel=4,
                )
            samples = self._sample_correlated(
                xk, correlation, rng, n_pop, n_mc, is_series
            )
        else:
            samples = self._sample_independent(
                xk, distributions, rng, n_pop, n_mc, is_series
            )

        # --- Evaluate the model on all samples ---
        # model_fn receives a dict of 2-D (or 1-D) arrays
        sample_dict = {col: samples[i] for i, col in enumerate(xk)}
        output_samples = np.asarray(model_fn(sample_dict), dtype=float)
        # Shape: (n_pop, n_mc) for DataFrame, (n_mc,) for Series

        # --- Aggregate results ---
        axis = -1  # MC dimension is always the last axis

        central = np.mean(output_samples, axis=axis)
        std_unc = np.std(output_samples, axis=axis, ddof=1)
        lower = np.quantile(output_samples, alpha / 2.0, axis=axis)
        upper = np.quantile(output_samples, 1.0 - alpha / 2.0, axis=axis)

        if is_series:
            self.df[output_name] = float(central)
            self.udf[output_name] = float(std_unc)
            self._coverage_intervals[output_name] = (
                float(lower), float(upper)
            )
        else:
            self.df[output_name] = central
            self.udf[output_name] = std_unc
            self._coverage_intervals[output_name] = (
                pd.Series(lower, index=self.df.index),
                pd.Series(upper, index=self.df.index),
            )

    def _sample_independent(
        self,
        xk: list[str],
        distributions: list[str],
        rng: np.random.Generator,
        n_pop: int,
        n_mc: int,
        is_series: bool,
    ) -> list[np.ndarray]:
        """Draw independent samples for each input variable.

        Returns a list of ndarrays, one per variable.
        Shape per array: ``(n_mc,)`` for Series, ``(n_pop, n_mc)`` for
        DataFrame.
        """
        samples = []

        for i, col in enumerate(xk):
            if is_series:
                mu = float(self.df[col])
                u = float(self.udf[col])
            else:
                mu = self.df[col].to_numpy(dtype=float)    # (n_pop,)
                u = self.udf[col].to_numpy(dtype=float)    # (n_pop,)

            dist = distributions[i]

            if dist == "normal":
                # u is directly the standard deviation of the Gaussian
                if is_series:
                    s = rng.normal(loc=mu, scale=u, size=(n_mc,))
                else:
                    z = rng.standard_normal(size=(n_pop, n_mc))
                    s = mu[:, np.newaxis] + u[:, np.newaxis] * z

            elif dist == "uniform":
                # Symmetric U(mu - h, mu + h); std = h / sqrt(3) => h = u*sqrt(3)
                h = u * np.sqrt(3.0)
                # Draw U(0, 1) and rescale to U(mu - h, mu + h)
                z = rng.uniform(size=(n_mc,) if is_series else (n_pop, n_mc))
                if is_series:
                    s = (mu - h) + 2.0 * h * z
                else:
                    s = (
                        (mu - h)[:, np.newaxis]
                        + 2.0 * h[:, np.newaxis] * z
                    )

            elif dist == "triangular":
                # Symmetric triangular on [mu - h, mu + h]; std = h/sqrt(6)
                # => h = u * sqrt(6).
                # Convolution identity: Z1 + Z2 - 1 ~ Triangular(-1, 0, 1)
                # where Z1, Z2 ~ U(0, 1).
                h = u * np.sqrt(6.0)
                size = (n_mc,) if is_series else (n_pop, n_mc)
                z = rng.uniform(size=size) + rng.uniform(size=size) - 1.0
                if is_series:
                    s = mu + h * z
                else:
                    s = mu[:, np.newaxis] + h[:, np.newaxis] * z

            samples.append(s)

        return samples

    def _validate_correlation(
        self, R: np.ndarray, nvar: int
    ) -> np.ndarray:
        """Validate and return the correlation matrix as a float ndarray."""
        R = np.asarray(R, dtype=float)
        if R.shape != (nvar, nvar):
            raise ValueError(
                f"correlation must have shape ({nvar}, {nvar}), "
                f"got {R.shape}."
            )
        if not np.allclose(np.diag(R), 1.0):
            raise ValueError(
                "Diagonal of the correlation matrix must be 1. "
                "Did you accidentally pass a covariance matrix?"
            )
        try:
            np.linalg.cholesky(R)
        except np.linalg.LinAlgError:
            raise ValueError(
                "Correlation matrix is not positive definite."
            )
        return R

    def _sample_correlated(
        self,
        xk: list[str],
        correlation: np.ndarray,
        rng: np.random.Generator,
        n_pop: int,
        n_mc: int,
        is_series: bool,
    ) -> list[np.ndarray]:
        """Draw correlated normal samples using a correlation matrix.

        The per-row covariance Σ_r = diag(u_r) @ R @ diag(u_r) is
        handled efficiently via a single Cholesky decomposition of R
        followed by per-row scaling with the uncertainties from *udf*.

        Returns a list of ndarrays, one per variable.
        Shape per array: ``(n_mc,)`` for Series, ``(n_pop, n_mc)`` for
        DataFrame.
        """
        nvar = len(xk)
        R = self._validate_correlation(correlation, nvar)
        # Cholesky factor of the correlation matrix: R = L_R @ L_R.T
        L_R = np.linalg.cholesky(R)   # shape (nvar, nvar)

        if is_series:
            # Single measurement: Sigma = diag(u) @ R @ diag(u)
            u_vec = np.array([float(self.udf[col]) for col in xk])
            mu_vec = np.array([float(self.df[col]) for col in xk])
            # L_Sigma = diag(u) @ L_R  (lower triangular Cholesky of Sigma)
            L_Sigma = u_vec[:, np.newaxis] * L_R   # (nvar, nvar)
            # Draw standard normal (n_mc, nvar), apply L_Sigma, shift by mean
            eps = rng.standard_normal(size=(n_mc, nvar))
            draw = eps @ L_Sigma.T + mu_vec          # (n_mc, nvar)
            return [draw[:, i] for i in range(nvar)]

        # DataFrame: per-row uncertainties u_r; shared correlation structure.
        # Vectorised Cholesky trick (no Python loop over rows):
        #   z_r = u_r ⊙ (L_R @ epsilon_r),  epsilon_r ~ N(0, I)
        # which has covariance diag(u_r) @ R @ diag(u_r) = Sigma_r.

        u_matrix = np.column_stack(
            [self.udf[col].to_numpy(dtype=float) for col in xk]
        )  # shape (n_pop, nvar)
        mu_matrix = np.column_stack(
            [self.df[col].to_numpy(dtype=float) for col in xk]
        )  # shape (n_pop, nvar)

        # Draw uncorrelated standard normals: (n_pop, n_mc, nvar)
        eps = rng.standard_normal(size=(n_pop, n_mc, nvar))
        # Apply correlation: eps @ L_R.T gives shape (n_pop, n_mc, nvar)
        # where each [r, :, :] row has covariance R (unit variance).
        z = eps @ L_R.T
        # Scale by per-row uncertainties: broadcast (n_pop, 1, nvar)
        z *= u_matrix[:, np.newaxis, :]
        # Shift by per-row means
        z += mu_matrix[:, np.newaxis, :]

        return [z[:, :, i] for i in range(nvar)]

    # ------------------------------------------------------------------
    # Private — linear propagation (GUM §5.1.2)
    # ------------------------------------------------------------------

    def _propagate_linear(
        self,
        xk: list[str],
        model_fn,
        output_name: str,
        alpha: float,
        correlation: np.ndarray | None,
        step_size: float,
    ) -> None:
        """First-order GUM uncertainty propagation (JCGM 100:2008, §5.1.2).

        The combined variance is::

            u_c²(y) = Σ_i  c_i² · u²(Xi)
                    + Σ_{i≠j} c_i · c_j · R[i,j] · u(Xi) · u(Xj)

        where ``c_i = ∂f/∂Xi`` is evaluated by central finite differences
        and R is the correlation matrix.  The per-row covariance term
        ``R[i,j] · u(Xi)[row] · u(Xj)[row]`` is computed directly from
        the per-row uncertainties in *udf*, guaranteeing consistency even
        when uncertainties vary across rows.

        The coverage interval uses the large-dof approximation
        ``U = k · u_c``,  ``k = z_{1-α/2}``.
        """
        self._validate_inputs(xk)

        is_series = isinstance(self.df, pd.Series)

        # Central value
        central_input = {col: self.df[col] for col in xk}
        central_output = np.asarray(model_fn(central_input), dtype=float)

        # Sensitivity coefficients c_i = ∂f/∂Xi via central finite differences
        sensitivities = {}
        for col in xk:
            if is_series:
                nominal = float(self.df[col])
                # Adaptive step proportional to |nominal|, with a floor
                h = step_size * max(abs(nominal), 1e-10)
            else:
                nominal = self.df[col].to_numpy(dtype=float)
                h = step_size * np.maximum(np.abs(nominal), 1e-10)

            # Create perturbed dicts; dict(central_input) is a shallow copy,
            # which is safe because we only replace one key per iteration.
            perturbed_plus = dict(central_input)
            perturbed_minus = dict(central_input)
            perturbed_plus[col] = self.df[col] + h
            perturbed_minus[col] = self.df[col] - h

            f_plus = np.asarray(model_fn(perturbed_plus), dtype=float)
            f_minus = np.asarray(model_fn(perturbed_minus), dtype=float)
            sensitivities[col] = (f_plus - f_minus) / (2.0 * h)

        # Combined variance: Σ_i c_i² · u_i²
        u_c_sq = sum(
            sensitivities[col] ** 2
            * np.asarray(self.udf[col], dtype=float) ** 2
            for col in xk
        )

        # Cross-covariance terms (GUM §5.2.2):
        #   Σ_{i≠j} c_i · c_j · R[i,j] · u(Xi) · u(Xj)
        # The double loop covers both (i,j) and (j,i), equivalent to
        # 2·Σ_{i<j} since R is symmetric.
        # Per-row u(Xi)·u(Xj) is taken directly from udf so the covariance
        # is always consistent with the actual row uncertainties.
        if correlation is not None:
            R = self._validate_correlation(correlation, len(xk))
            for i, col_i in enumerate(xk):
                for j, col_j in enumerate(xk):
                    if i != j:
                        u_i = np.asarray(self.udf[col_i], dtype=float)
                        u_j = np.asarray(self.udf[col_j], dtype=float)
                        u_c_sq = u_c_sq + (
                            sensitivities[col_i]
                            * sensitivities[col_j]
                            * R[i, j]
                            * u_i * u_j
                        )

        u_c = np.sqrt(u_c_sq)

        # Coverage factor k for the Gaussian large-dof approximation
        k = _norm.ppf(1.0 - alpha / 2.0)
        half_width = k * u_c

        if is_series:
            c = float(central_output)
            u = float(u_c)
            hw = float(half_width)
            self.df[output_name] = c
            self.udf[output_name] = u
            self._coverage_intervals[output_name] = (c - hw, c + hw)
        else:
            self.df[output_name] = central_output
            self.udf[output_name] = u_c
            self._coverage_intervals[output_name] = (
                pd.Series(
                    central_output - half_width, index=self.df.index
                ),
                pd.Series(
                    central_output + half_width, index=self.df.index
                ),
            )


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    # --- Shared test data ---
    # Ideal-gas density: rho = P / (R * T)
    # Analytical sensitivities: d(rho)/dP = 1/(R*T), d(rho)/dT = -P/(R*T^2)
    R = 287.058  # specific gas constant for dry air [J/(kg·K)]

    data = {"P": [100_000.0, 101_325.0, 95_000.0],   # Pa
            "T": [293.15,    298.15,    288.15]}       # K
    udata = {"P": [500.0,    200.0,    300.0],         # Pa (1-sigma)
             "T": [0.5,      0.5,      0.5]}           # K  (1-sigma)

    df = pd.DataFrame(data)
    udf = pd.DataFrame(udata)

    def density(d):
        """Ideal-gas density rho = P / (R * T)."""
        return d["P"] / (R * d["T"])

    # --- Example 1: Monte Carlo, uncorrelated normal inputs ---
    print("=" * 60)
    print("Example 1 — Monte Carlo (uncorrelated, normal inputs)")
    print("=" * 60)

    pdf_mc = ProbabilisticDataFrame(df.copy(), udf.copy())
    pdf_mc.propagate(
        xk=["P", "T"],
        model_fn=density,
        output_name="rho",
        method="MC",
        alpha=0.05,
        seed=0,
    )
    low_mc, high_mc = pdf_mc.coverage_interval("rho")
    print(pdf_mc.df[["P", "T", "rho"]].to_string())
    print("\nStandard uncertainties:")
    print(pdf_mc.udf[["P", "T", "rho"]].to_string())
    print("\n95 % coverage interval (lower):")
    print(low_mc.to_string())
    print("95 % coverage interval (upper):")
    print(high_mc.to_string())

    # --- Example 2: Monte Carlo, uniform inputs ---
    print("\n" + "=" * 60)
    print("Example 2 — Monte Carlo (uncorrelated, uniform inputs)")
    print("=" * 60)

    pdf_mc_u = ProbabilisticDataFrame(df.copy(), udf.copy())
    pdf_mc_u.propagate(
        xk=["P", "T"],
        model_fn=density,
        output_name="rho",
        method="MC",
        distributions=["uniform", "normal"],
        alpha=0.05,
        seed=0,
    )
    low_u, high_u = pdf_mc_u.coverage_interval("rho")
    print(pdf_mc_u.udf[["P", "T", "rho"]].to_string())

    # --- Example 3: Monte Carlo, correlated inputs ---
    print("\n" + "=" * 60)
    print("Example 3 — Monte Carlo (correlated inputs, r_PT = 0.6)")
    print("=" * 60)

    # Correlation matrix (dimensionless, diagonal = 1).
    # The actual per-row covariance cov(P,T) = r * u(P)[row] * u(T)[row]
    # is reconstructed internally, guaranteeing consistency for all rows.
    r_corr = 0.6
    corr_matrix = np.array([
        [1.0,    r_corr],
        [r_corr, 1.0   ],
    ])

    pdf_mc_c = ProbabilisticDataFrame(df.copy(), udf.copy())
    pdf_mc_c.propagate(
        xk=["P", "T"],
        model_fn=density,
        output_name="rho",
        method="MC",
        correlation=corr_matrix,
        alpha=0.05,
        seed=0,
    )
    print(pdf_mc_c.udf[["P", "T", "rho"]].to_string())

    # --- Example 4: linear (GUM §5.1.2) ---
    print("\n" + "=" * 60)
    print("Example 4 — Linear propagation (GUM §5.1.2)")
    print("=" * 60)

    pdf_lin = ProbabilisticDataFrame(df.copy(), udf.copy())
    pdf_lin.propagate(
        xk=["P", "T"],
        model_fn=density,
        output_name="rho",
        method="linear",
        alpha=0.05,
    )
    low_lin, high_lin = pdf_lin.coverage_interval("rho")
    print(pdf_lin.df[["P", "T", "rho"]].to_string())
    print("\nStandard uncertainties:")
    print(pdf_lin.udf[["P", "T", "rho"]].to_string())
    print("\n95 % coverage interval (lower):")
    print(low_lin.to_string())
    print("95 % coverage interval (upper):")
    print(high_lin.to_string())

    # --- Comparison: MC vs linear ---
    print("\n" + "=" * 60)
    print("Comparison — u(rho):  MC vs linear")
    print("=" * 60)
    comparison = pd.DataFrame({
        "u_rho_MC":     pdf_mc.udf["rho"],
        "u_rho_linear": pdf_lin.udf["rho"],
    })
    print(comparison.to_string())
