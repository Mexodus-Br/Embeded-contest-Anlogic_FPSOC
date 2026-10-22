#pragma once
// Linaro GCC 7.5 exposes the filesystem TS; newer toolchains provide C++17.
#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ < 8
#include <experimental/filesystem>
namespace ps_fs=std::experimental::filesystem;
#else
#include <filesystem>
namespace ps_fs=std::filesystem;
#endif
