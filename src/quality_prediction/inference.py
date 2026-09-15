"""Quality-model inference over an in-memory HTRflow document tree."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np

from quality_prediction.core.geometry import BBox
from quality_prediction.features.page import PageFeatureExtractor
from quality_prediction.features.binning import (
    ConfidenceBinFitter,
)
from quality_prediction.io.htr_json import (
    PageDocument,
    TextLine,
    TextRegion,
    TextResult,
)


JSON_FEATURE_GROUPS = (
    "segmentation",
    "layout",
    "htr_confidence",
    "text",
)


def _bbox(node: Any, offset: tuple[float, float] = (0.0, 0.0)) -> BBox:
    box = node.polygon.bbox
    dx, dy = offset
    return BBox(box.xmin + dx, box.ymin + dy, box.xmax + dx, box.ymax + dy)


def _child_offset(parent: Any) -> tuple[float, float]:
    """Detect whether nested polygons are crop-local or already page-absolute."""
    parent_box = _bbox(parent)
    origin = (parent_box.xmin, parent_box.ymin)

    def contains(box: BBox) -> bool:
        x, y = box.center
        return (
            parent_box.xmin <= x <= parent_box.xmax
            and parent_box.ymin <= y <= parent_box.ymax
        )

    raw_score = sum(contains(_bbox(child)) for child in parent.regions)
    translated_score = sum(contains(_bbox(child, origin)) for child in parent.regions)
    return origin if translated_score > raw_score else (0.0, 0.0)


def _line(node: Any, offset: tuple[float, float]) -> TextLine | None:
    if not node.transcription:
        return None
    transcription = node.transcription[0]
    polygon = node.polygon.move(offset) if offset != (0.0, 0.0) else node.polygon
    return TextLine(
        label=str(node.annotations.get("label", "")),
        text_result=TextResult(
            [transcription.text],
            [transcription.confidence] if transcription.confidence is not None else [],
        ),
        token_scores=list(transcription.token_scores),
        words=[],
        segmentation_label=str(node.annotations.get("segmentation_label", "textline")),
        segmentation_confidence=node.annotations.get("segmentation_confidence"),
        bbox=_bbox(node, offset),
        polygon=str(polygon),
    )


def page_document_from_htrflow(document: Any) -> PageDocument:
    """Adapt a live HTRflow document without serializing it to JSON."""
    regions: list[TextRegion] = []
    lines: list[TextLine] = []
    for node in document.regions:
        if node.regions:
            offset = _child_offset(node)
            region_lines = [
                line
                for child in node.regions
                if (line := _line(child, offset)) is not None
            ]
            regions.append(
                TextRegion(
                    label=str(node.annotations.get("label", "")),
                    lines=region_lines,
                    segmentation_label=str(
                        node.annotations.get("segmentation_label", "textregion")
                    ),
                    segmentation_confidence=node.annotations.get(
                        "segmentation_confidence"
                    ),
                    bbox=_bbox(node),
                    polygon=str(node.polygon),
                )
            )
        elif (line := _line(node, (0.0, 0.0))) is not None:
            lines.append(line)

    return PageDocument(
        file_name=document.image_name,
        image_path=str(document._image_path),
        image_name=document.image_name,
        label="",
        regions=regions,
        lines=lines,
    )


class XGBoostQualityPredictor:
    """Load a trained model and predict from HTRflow's document state."""

    def __init__(
        self,
        model: str | Path,
        feature_groups: Iterable[str] = JSON_FEATURE_GROUPS,
        feature_names: Iterable[str] | None = None,
        bin_config: str | Path | None = None,
    ):
        import joblib

        self.model_path = Path(model)
        self.bin_config_path = (
            Path(bin_config)
            if bin_config is not None
            else None
        )

        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Quality-prediction model does not exist: "
                f"{self.model_path}"
            )

        self.model = joblib.load(self.model_path)
        self.feature_groups = tuple(feature_groups)
        self.feature_names = tuple(
            feature_names or self._model_feature_names()
        )

        if not self.feature_names:
            raise ValueError(
                "The model has no feature names; "
                "configure feature_names"
            )

        confidence_bins = None

        if self.bin_config_path is not None:
            if not self.bin_config_path.is_file():
                raise FileNotFoundError(
                    "Confidence bin configuration does not exist: "
                    f"{self.bin_config_path}"
                )

            confidence_bins = ConfidenceBinFitter().load(
                str(self.bin_config_path)
            )

        self.extractor = PageFeatureExtractor(
            bin_config=confidence_bins,
        )

    def _model_feature_names(self) -> list[str]:
        names = getattr(self.model, "feature_names_in_", None)
        if names is None and hasattr(self.model, "get_booster"):
            names = self.model.get_booster().feature_names
        return [] if names is None else list(names)

    def predict(self, document: Any) -> float:
        import pandas as pd

        features = self.extractor.extract_features(
            page_document_from_htrflow(document), self.feature_groups
        )
        row = pd.DataFrame(
            [{name: features.get(name, np.nan) for name in self.feature_names}]
        )
        return float(self.model.predict(row)[0])
