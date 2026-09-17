#include <memory>

#include "attention_fetch.hpp"
#include "common.hpp"
#include "experts.hpp"
#include "mixed.hpp"
#include "pipeline.hpp"
int main(int argc, char** argv) {
  require(argc == 2 && getenv("SLURM_JOB_ID"), "usage inside allocation: llm_streams CASE");
  Context context;
  puts(
      "benchmark,config,schedule,phase,submission,trial,gpu_us,host_us,submit_us,max_abs_error,"
      "work_bytes,correct");
  std::string name = argv[1];
  if (name == "attention_fetch")
    benchmark_attention_fetch(context);
  else if (name == "pipeline")
    benchmark_pipeline(context);
  else if (name == "experts")
    benchmark_experts(context);
  else if (name == "mixed")
    benchmark_mixed(context);
  else
    require(false, "unknown case");
  HIP(hipDeviceSynchronize());
  Context::print_maps();
  return 0;
}
