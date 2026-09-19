#pragma once
#include <stdint.h>
struct alignas(64) LayerState {
  uint64_t started[2];
  uint64_t value[2];
  uint64_t completed[2];
  uint64_t expected[2];
};
struct Sample {
  uint64_t start, end, saw_peer, input_ok, value, block;
};
struct Args {
  LayerState* states;
  Sample* samples;
  uint64_t delay_ticks, rendezvous_ticks, epoch;
  uint32_t layer, role, blocks, reserved;
};
static_assert(sizeof(LayerState) == 64 && sizeof(Sample) == 48 && sizeof(Args) == 56);
