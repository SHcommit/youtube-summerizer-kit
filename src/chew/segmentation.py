"""Chapter-first transcript segmentation (re-exported from pipeline)."""

from chew.pipeline.segmentation import (
    BoundaryDetector,
    PausePunctuationBoundaryDetector,
    SegmentationPolicy,
    SegmentManifest,
    segment_transcript,
)

__all__ = [
    "BoundaryDetector",
    "PausePunctuationBoundaryDetector",
    "SegmentManifest",
    "SegmentationPolicy",
    "segment_transcript",
]
