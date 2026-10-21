"""GeoTIFF submission writer + validator for the DOE GEMS Prize Challenge.

Required format (verbatim from the organizer's page, verified 2026-10-21):
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format

    - same projected CRS as the training data: UTM zone 11N, EPSG:32611
    - same resolution as the training data: 100 m
    - same bounds as the training data; data outside the bounds is null or NaN
    - single band, float32, values in [0, 1] (confidence of fault presence)

Root cause of the error the user hit, "Predicted values must be in range
[0, 1]" -- there are exactly two documented mechanisms, and this module
closes both:

    1. THE SENTINEL MECHANISM. `training_features.tif` (and some derived
       rasters) use a 32-bit-float minimum sentinel, -3.4028234663852886e+38,
       as a "nodata" flag. If that sentinel (or any other out-of-range
       nodata value) survives into the written band -- even on pixels the
       author considers "outside the footprint" -- the validator reads a
       value < 0 and rejects the whole file.
    2. THE NaN-WITH-NODATA-TAG MECHANISM. Writing `nodata=nan` is a legal
       way to mark "outside the footprint" per the spec ("null or nan"), but
       it is one off-by-one / resampling step away from a stray NaN leaking
       inside the footprint, which some validator implementations treat as
       out-of-range. The safest, most conservative choice -- and the one
       this module defaults to -- is to write **every single pixel in the
       raster, including outside the study-area footprint, as a finite
       value in [0, 1]** (0.0 is the natural, organizer-sanctioned choice:
       "a sample submission that predicts total fault absence" uses exactly
       that value), and to omit a nodata tag entirely (`nodata=None`).

Nothing here is invented: both mechanisms were independently diagnosed from
the organizer's own format requirements plus the reference solution's own
loader (`X_orig[X_orig < -1e38] = np.nan`, in
https://github.com/drivendataorg/gems-prize-reference-solution,
unet-mc-cv-reference-solution.ipynb, cell 5 -- that is the exact sentinel
value this module strips).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

FLOAT32_NEG_SENTINEL = np.float32(-3.4028234663852886e38)
EXPECTED_CRS_EPSG = 32611
EXPECTED_RESOLUTION_M = 100.0


@dataclass
class SubmissionTemplate:
    """Geometry/CRS contract a submission must match, read from a real
    organizer-provided raster (training_features.tif, labels.tif, or
    sample_submission.tif). Never hand-type these numbers -- always derive
    them with `SubmissionTemplate.from_raster`.
    """

    height: int
    width: int
    transform: tuple  # affine 6-tuple (a, b, c, d, e, f), rasterio convention
    crs_epsg: int
    source_file: str = ""
    source_sha256: str = ""

    @classmethod
    def from_raster(cls, path: str) -> "SubmissionTemplate":
        import rasterio

        p = Path(path)
        with rasterio.open(p) as src:
            if src.crs is None or src.crs.to_epsg() != EXPECTED_CRS_EPSG:
                raise ValueError(
                    f"{path}: CRS is {src.crs}, expected EPSG:{EXPECTED_CRS_EPSG} per the "
                    "organizer's submission-format spec"
                )
            res_x, res_y = src.res
            if not (np.isclose(res_x, EXPECTED_RESOLUTION_M) and np.isclose(res_y, EXPECTED_RESOLUTION_M)):
                raise ValueError(
                    f"{path}: resolution is {src.res}, expected ({EXPECTED_RESOLUTION_M}, "
                    f"{EXPECTED_RESOLUTION_M}) m per the organizer's spec"
                )
            return cls(
                height=src.height,
                width=src.width,
                transform=tuple(src.transform)[:6],
                crs_epsg=EXPECTED_CRS_EPSG,
                source_file=str(p),
                source_sha256=_sha256_of_file(p),
            )


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sanitize_prediction(array: np.ndarray, footprint_mask: np.ndarray | None = None) -> np.ndarray:
    """Force an arbitrary float array into the organizer's required shape:
    float32, every cell finite, every cell in [0, 1], no sentinel values.

    `footprint_mask`, if given, is True where real study-area data exists;
    everywhere else is forced to 0.0 (not NaN), which is the single safest
    choice because it can never trip a "[0,1]" validator regardless of how
    strict it is about nodata handling, at the cost of being slightly less
    "spec-literal" than writing NaN outside the footprint. Both are legal
    per the spec ("null or nan"); this project picks 0.0 as the
    belt-and-suspenders default and also ships a NaN-outside twin via
    `write_submission(..., outside_footprint="nan")` for teams who want the
    literal null/NaN form.
    """
    out = np.asarray(array, dtype=np.float64).copy()

    # Strip the documented float32 sentinel and any other non-finite cell.
    out[out <= float(FLOAT32_NEG_SENTINEL) * 0.999] = np.nan  # anything sentinel-like
    bad = ~np.isfinite(out)
    out[bad] = 0.0

    if footprint_mask is not None:
        out = np.where(footprint_mask, out, 0.0)

    out = np.clip(out, 0.0, 1.0)
    return out.astype(np.float32)


@dataclass
class ValidationReport:
    ok: bool
    checks: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps({"ok": self.ok, "checks": self.checks, "errors": self.errors}, indent=2)


def validate_submission(path: str, template: SubmissionTemplate | None = None) -> ValidationReport:
    """Re-open a written GeoTIFF from disk and check every requirement the
    organizer's submission form and rules enforce. This is the exact
    function that must pass before anyone is told a file is submit-ready.
    """
    import rasterio

    errors: list[str] = []
    checks: dict = {}

    with rasterio.open(path) as src:
        checks["band_count"] = src.count
        if src.count != 1:
            errors.append(f"expected a single band, found {src.count}")

        checks["dtype"] = src.dtypes[0]
        if src.dtypes[0] != "float32":
            errors.append(f"expected dtype float32, found {src.dtypes[0]}")

        epsg = src.crs.to_epsg() if src.crs else None
        checks["crs_epsg"] = epsg
        if epsg != EXPECTED_CRS_EPSG:
            errors.append(f"expected CRS EPSG:{EXPECTED_CRS_EPSG}, found {src.crs}")

        checks["resolution_m"] = list(src.res)
        if not (np.isclose(src.res[0], EXPECTED_RESOLUTION_M) and np.isclose(src.res[1], EXPECTED_RESOLUTION_M)):
            errors.append(f"expected 100 m resolution, found {src.res}")

        checks["shape"] = [src.height, src.width]
        checks["transform"] = list(src.transform)[:6]
        if template is not None:
            if (src.height, src.width) != (template.height, template.width):
                errors.append(
                    f"shape {(src.height, src.width)} != template shape "
                    f"{(template.height, template.width)}"
                )
            if tuple(src.transform)[:6] != template.transform:
                errors.append("affine transform does not match the template")

        data = src.read(1)
        checks["nodata_tag"] = src.nodata

        n_nan = int(np.isnan(data).sum())
        checks["n_nan"] = n_nan
        n_below = int((data < 0).sum()) if np.isfinite(data).any() else 0
        n_above = int((data > 1).sum()) if np.isfinite(data).any() else 0
        finite = np.isfinite(data)
        if finite.any():
            n_below = int((data[finite] < 0).sum())
            n_above = int((data[finite] > 1).sum())
        checks["n_below_zero"] = n_below
        checks["n_above_one"] = n_above
        checks["min_finite"] = float(np.nanmin(data)) if finite.any() else None
        checks["max_finite"] = float(np.nanmax(data)) if finite.any() else None
        checks["n_predicted_px_gt_0"] = int((data[finite] > 0).sum()) if finite.any() else 0

        if n_below or n_above:
            errors.append(
                f"{n_below + n_above} cells fall outside [0, 1] "
                f"(min={checks['min_finite']}, max={checks['max_finite']}); "
                "this is exactly the organizer's \"Predicted values must be in range [0, 1]\" rejection"
            )
        if n_nan > 0 and src.nodata is None:
            errors.append(
                f"{n_nan} NaN cells present but nodata tag is None -- some validators treat "
                "untagged NaN as an out-of-range value; either set nodata=nan or remove the NaNs"
            )

    checks["sha256"] = _sha256_of_file(Path(path))
    return ValidationReport(ok=(len(errors) == 0), checks=checks, errors=errors)


def write_submission(
    array: np.ndarray,
    out_path: str,
    template: SubmissionTemplate,
    footprint_mask: np.ndarray | None = None,
    outside_footprint: str = "zero",
) -> ValidationReport:
    """Write a single-band float32 GeoTIFF that matches `template` exactly
    and passes `validate_submission`. Always re-validates the file it just
    wrote by re-opening it from disk (never trust the in-memory array).
    """
    import rasterio
    from rasterio.transform import Affine

    if array.shape != (template.height, template.width):
        raise ValueError(f"array shape {array.shape} != template shape {(template.height, template.width)}")

    clean = sanitize_prediction(array, footprint_mask=None)  # clip/sanitize first
    if footprint_mask is not None:
        if outside_footprint == "nan":
            clean = np.where(footprint_mask, clean, np.nan).astype(np.float32)
        else:
            clean = np.where(footprint_mask, clean, 0.0).astype(np.float32)

    nodata_value = np.nan if (outside_footprint == "nan" and footprint_mask is not None) else None

    profile = {
        "driver": "GTiff",
        "height": template.height,
        "width": template.width,
        "count": 1,
        "dtype": "float32",
        "crs": f"EPSG:{template.crs_epsg}",
        "transform": Affine(*template.transform),
        "nodata": nodata_value,
        "compress": "deflate",
        "predictor": 2,
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(clean, 1)

    return validate_submission(out_path, template=template)
