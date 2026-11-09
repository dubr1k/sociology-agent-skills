"""Синтетические проверки API; не эмпирические результаты и не выбор теста."""
import json
import math
import sys
from importlib.metadata import version
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.power import FTestAnovaPower, tt_ind_solve_power


def finite_vector(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or x.size < 2 or not np.isfinite(x).all():
        raise ValueError("Нужен одномерный конечный массив с n >= 2")
    if np.var(x, ddof=1) <= 0:
        raise ValueError("Вырожденная выборка требует отдельного решения")
    return x


def welch_summary(a, b, confidence=0.95):
    """A − B; интервал относится к разности, не к Cohen d."""
    if not 0 < confidence < 1:
        raise ValueError("Уровень интервала должен лежать между 0 и 1")
    a, b = finite_vector(a), finite_vector(b)
    va, vb = a.var(ddof=1), b.var(ddof=1)
    qa, qb = va / len(a), vb / len(b)
    se = np.sqrt(qa + qb)
    df = (qa + qb)**2 / (qa**2 / (len(a)-1) + qb**2 / (len(b)-1))
    diff = a.mean() - b.mean()
    critical = stats.t.ppf((1 + confidence)/2, df)
    test = stats.ttest_ind(a, b, equal_var=False, alternative="two-sided")
    pooled = np.sqrt(((len(a)-1)*va + (len(b)-1)*vb) / (len(a)+len(b)-2))
    assert np.isclose(test.statistic, diff / se)
    return {"n_a": len(a), "n_b": len(b), "mean_difference_a_minus_b": float(diff),
            "ci_difference": [float(diff-critical*se), float(diff+critical*se)],
            "confidence": confidence, "t": float(test.statistic), "df": float(df),
            "p_two_sided": float(test.pvalue), "cohen_d_pooled_signed": float(diff/pooled)}


def main():
    # До использования выводятся фактически установленные версии.
    versions = {p: version(p) for p in ("numpy", "scipy", "statsmodels")}
    print(json.dumps({"python": sys.version.split()[0], "packages": versions}, ensure_ascii=False))
    rng = np.random.default_rng(42)
    a, b = rng.normal(0.4, 1, 35), rng.normal(0, 1.7, 40)
    welch = welch_summary(a, b)
    # Для независимых групп знаменатель d описан; ДИ d здесь не рассчитывается.
    assert welch["ci_difference"][0] < welch["mean_difference_a_minus_b"] < welch["ci_difference"][1]
    for invalid in ([1, np.nan, 2], [1, np.inf, 2], [1, 1, 1], [[1, 2], [3, 4]]):
        try:
            finite_vector(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Некорректный вход не отклонён")

    # Пары уже выровнены по ID; NaN в любой волне удаляет пару, не отдельное значение.
    pre = rng.normal(10, 2, 30)
    post = pre + rng.normal(0.5, 1.2, 30)
    post[0] = np.nan
    if np.isinf(pre).any() or np.isinf(post).any():
        raise ValueError("Бесконечность в парных данных — ошибка входа, не пропуск")
    keep = ~np.isnan(pre) & ~np.isnan(post)
    delta = finite_vector(post[keep] - pre[keep])
    paired = stats.ttest_rel(post[keep], pre[keep], alternative="two-sided")
    assert np.isclose(paired.statistic, stats.ttest_1samp(delta, 0).statistic)
    se_delta = stats.sem(delta)
    ci_delta = stats.t.interval(0.95, len(delta)-1, loc=delta.mean(), scale=se_delta)

    # HC3 задан заранее для независимых ошибок; не для кластерной панели.
    x = rng.normal(size=80)
    y = 1 + 0.6*x + rng.normal(size=80)*(0.5 + np.abs(x))
    X = sm.add_constant(x)
    assert np.linalg.matrix_rank(X) == X.shape[1]
    fit = sm.OLS(y, X, missing="raise").fit(cov_type="HC3")
    assert np.isfinite(fit.params).all() and np.isfinite(fit.conf_int()).all()

    # Планировочные модели независимых наблюдений с общей дисперсией.
    n_group = math.ceil(tt_ind_solve_power(effect_size=0.5, alpha=0.05,
                                         power=0.8, ratio=1, alternative="two-sided"))
    raw_total = FTestAnovaPower().solve_power(effect_size=0.25, k_groups=3,
                                             alpha=0.05, power=0.8)
    anova_per_group = math.ceil(raw_total/3)
    detectable = tt_ind_solve_power(effect_size=None, nobs1=50, ratio=1,
                                   alpha=0.05, power=0.8, alternative="two-sided")
    print(json.dumps({"synthetic_only": True, "welch": welch,
                      "paired": {"complete_pairs": int(keep.sum()), "omitted_pairs": int((~keep).sum()),
                                 "mean_post_minus_pre": float(delta.mean()),
                                 "ci_difference": list(map(float, ci_delta)),
                                 "d_z": float(delta.mean()/delta.std(ddof=1)),
                                 "t": float(paired.statistic), "p": float(paired.pvalue)},
                      "ols_hc3": {"coefficients": fit.params.tolist(), "ci": fit.conf_int().tolist()},
                      "planning": {"t_n_per_group": n_group,
                                   "anova_n_per_group": anova_per_group,
                                   "anova_total": 3*anova_per_group,
                                   "detectable_d_n50_per_group": float(detectable)}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
