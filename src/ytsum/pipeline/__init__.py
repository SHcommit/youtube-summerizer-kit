"""Hierarchical synthesis pipeline, segmentation, scheduler, and output compilation."""

from ytsum.pipeline.engine import (
    AnalysisPipeline,
    AnalysisResult,
    PipelineExecutionError,
    build_analysis_job_graph,
)
from ytsum.pipeline.knowledge import build_knowledge_pack
from ytsum.pipeline.outputs import OutputCompiler
from ytsum.pipeline.scheduler import AdaptiveLimiter, JobHandler, RateLimited, RunSummary, Scheduler
from ytsum.pipeline.segmentation import (
    BoundaryDetector,
    PausePunctuationBoundaryDetector,
    SegmentationPolicy,
    SegmentManifest,
    segment_transcript,
)

__all__ = [
    "AdaptiveLimiter",
    "AnalysisPipeline",
    "AnalysisResult",
    "BoundaryDetector",
    "JobHandler",
    "OutputCompiler",
    "PausePunctuationBoundaryDetector",
    "PipelineExecutionError",
    "RateLimited",
    "RunSummary",
    "Scheduler",
    "SegmentManifest",
    "SegmentationPolicy",
    "build_analysis_job_graph",
    "build_knowledge_pack",
    "segment_transcript",
]
