# This build needs only llvm-objcopy for the bundled GPU support shaders.
if(NOT TARGET llvm-objcopy)
  add_executable(llvm-objcopy IMPORTED GLOBAL)
  set_target_properties(llvm-objcopy PROPERTIES IMPORTED_LOCATION /opt/rocm/llvm/bin/llvm-objcopy)
endif()
set(LLVM_FOUND TRUE)
