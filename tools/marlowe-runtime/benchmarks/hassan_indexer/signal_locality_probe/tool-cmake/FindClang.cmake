# This build needs only the installed assembler executable, not libclang.
if(NOT TARGET clang)
  add_executable(clang IMPORTED GLOBAL)
  set_target_properties(clang PROPERTIES IMPORTED_LOCATION /opt/rocm/llvm/bin/clang)
endif()
set(Clang_FOUND TRUE)
