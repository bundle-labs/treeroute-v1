"""One definition of "this value is NoData, not data", applied where models READ the panel.

WHY A SHARED MODULE. The correct guard already existed --
    presplit_cc/add_drought_wbal_all_regions.py:101
        return (np.abs(a) >= 2 ** 31) | (a == -32768.0)
-- but it lived inside a single derived-column builder, so the panel kept storing the raw sentinels
and every model consumer read them as numbers. Copying the test into three loaders would repeat the
original mistake in triplicate; this is the one place it lives.

WHY fillna DOES NOT ALREADY HANDLE IT. -32768 is a perfectly finite float. Every NaN-based defence
in this project is blind to it -- reference_panel_nodata_sentinel records the same property
defeating an isfinite-based median fill. Masking to NaN FIRST is what lets the existing fillna and
median-imputation paths do their job.

THE THIRD VALUE, WHICH THIS CANNOT FIX. add_drought_wbal_all_regions' docstring warns that
    -2147483648 - (-32768) = -2147450880
is neither sentinel and 32,768 below the abs>=2**31 test. Any arithmetic performed on poisoned
values BEFORE masking -- a window mean, a difference, a ratio -- produces a number that no check can
recognise. D:/defo_matrix already contains such values in its _min/_mean/_max aggregates. Masking at
read time removes the exact sentinels and CANNOT recover those. Only rebuilding the matrix can.
"""
import numpy as np

# EXACT values, not a magnitude rule. gdd5_degC_days legitimately reaches ~1300 and population
# density far higher, so a threshold would discard real data. These are the specific integers
# GDAL/NetCDF writers emit for "no data", which no physical variable in this panel can take.
SENTINELS = (-32768.0, -32767.0, -2147483648.0, -2147483647.0)

# NetCDF/HDF5 float NoData. ACAG PM2.5 writes 9.96921e+36 (NC_FILL_FLOAT), read from the
# file header -- the target survey had GUESSED -999, which is wrong in the way that matters:
# the real value is POSITIVE, so a `< 0` guard never sees it, and it is FINITE, so isfinite
# passes it. One inside a mean makes the result ~1e36. A magnitude floor is used rather than
# an exact value because arithmetic on a fill (a window mean, a difference) lands near it but
# not on it, and no physical variable in this panel approaches 1e30.
HUGE = 1e30

# Columns that are identifiers or targets rather than measurements. Masking a key would silently
# drop rows in a join; masking a target would fabricate missingness in the thing being predicted.
NEVER_MASK = frozenset(["lat", "lon", "year", "month", "t", "k", "cell", "cell_id", "reg", "region",
                        "ecoid", "y", "yy", "is_train", "burned_frac", "n_valid", "side", "eco",
                        "sid", "date", "pos", "src"])


def mask(df, cols=None, log=None):
    """Replace exact NoData sentinels with NaN, in place. Returns (n_masked, columns_touched).

    Call this IMMEDIATELY after reading a panel file and BEFORE any arithmetic, shift, aggregation
    or fillna. Order matters: a lag shift moves a sentinel rather than removing it, and a window
    mean over one turns it into a value nothing can detect.
    """
    todo = [c for c in (cols if cols is not None else df.columns)
            if c not in NEVER_MASK and c in df.columns and df[c].dtype.kind in "fiu"]
    n, touched = 0, []
    for c in todo:
        v = df[c].to_numpy()
        m = np.isin(v, SENTINELS)
        if v.dtype.kind == "f":
            m = m | (np.abs(v) >= HUGE)
        if not m.any():
            continue
        k = int(m.sum())
        n += k
        touched.append((c, k))
        # float first: an int column cannot hold NaN, and assigning into one would silently cast
        # the sentinel to something else rather than removing it.
        df[c] = df[c].astype(np.float64).mask(m)
    if log is not None and touched:
        top = ", ".join("%s(%d)" % (c, k) for c, k in sorted(touched, key=lambda x: -x[1])[:4])
        log("    [sentinel] masked %s values to NaN across %d columns: %s"
            % (format(n, ","), len(touched), top))
    return n, touched


def audit(df, cols=None):
    """Count sentinels without modifying anything -- for checking whether a fix took."""
    todo = [c for c in (cols if cols is not None else df.columns)
            if c not in NEVER_MASK and c in df.columns and df[c].dtype.kind in "fiu"]
    def _hit(v):
        m = np.isin(v, SENTINELS)
        if v.dtype.kind == "f":
            m = m | (np.abs(v) >= HUGE)
        return m
    return {c: int(_hit(df[c].to_numpy()).sum())
            for c in todo if _hit(df[c].to_numpy()).any()}
