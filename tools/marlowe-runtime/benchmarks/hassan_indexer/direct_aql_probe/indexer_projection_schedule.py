from __future__ import annotations

import logging
from typing import Any

import torch

logger = logging.getLogger(__name__)


class IndexerProjectionSchedule:
    """Own ordinary projection events for one serialized target graph runner."""

    def __init__(self, mode: str, layer_ids: tuple[int, ...]) -> None:
        if mode not in ("serial", "events"):
            raise ValueError(f"Invalid indexer projection schedule: {mode}")
        if not layer_ids or len(set(layer_ids)) != len(layer_ids):
            raise ValueError("Indexer projection layers must be nonempty and unique")
        self.mode = mode
        self.stream = torch.cuda.Stream()
        self.layer_ids = layer_ids
        self.generation = 0
        self.eager_events = self._new_events()
        self.events = self.eager_events
        self.graph_events: dict[Any, Any] = {}
        self.census: set[tuple[int, int, bool]] = set()

    def _new_events(self) -> dict[int, tuple[torch.cuda.Event, torch.cuda.Event]]:
        return {
            layer_id: (
                torch.cuda.Event(enable_timing=False),
                torch.cuda.Event(enable_timing=False),
            )
            for layer_id in self.layer_ids
        }

    def prepare_capture(self, shape_key: Any) -> None:
        if (
            shape_key.size != 1
            or shape_key.stream_idx is not None
            or shape_key.variant_label is not None
        ):
            raise ValueError(f"Unsupported indexer projection graph: {shape_key}")
        # Recapture must retire the old graph's events before replacing its owner.
        torch.cuda.synchronize()
        self.generation += 1
        self.events = self._new_events()

    def finish_capture(self, shape_key: Any = None) -> None:
        if shape_key is not None:
            self.graph_events[shape_key] = (self.generation, self.events)
        self.events = self.eager_events

    def begin(self, layer_id: int, x: Any) -> None:
        capturing = torch.cuda.is_current_stream_capturing()
        census_key = (layer_id, self.generation, capturing)
        if census_key not in self.census:
            logger.info(
                "INDEXER_PROJECTION schedule=%s layer=%s generation=%s capture=%s rows=4",
                self.mode,
                layer_id,
                self.generation,
                capturing,
            )
            self.census.add(census_key)
        if self.mode == "events":
            main = torch.cuda.current_stream()
            self.events[layer_id][0].record(main)
            if not capturing:
                for tensor in x if isinstance(x, tuple) else (x,):
                    if isinstance(tensor, torch.Tensor):
                        tensor.record_stream(self.stream)

    def key(self, layer_id: int, projection: Any, x: Any) -> torch.Tensor:
        if self.mode == "serial":
            return projection(x)[0]
        main = torch.cuda.current_stream()
        ready, done = self.events[layer_id]
        with torch.cuda.stream(self.stream):
            self.stream.wait_event(ready)
            key, _ = projection(x)
            done.record(self.stream)
        main.wait_event(done)
        if not torch.cuda.is_current_stream_capturing():
            key.record_stream(main)
        return key

    def close(self) -> None:
        torch.cuda.synchronize()
        self.graph_events.clear()
        self.events = self.eager_events = {}
