# Contributing

## Getting started

```bash
git clone https://github.com/luokai0/luo-computer
cd luo-computer
cmake -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

## Code style
- C++17, no exceptions, no RTTI
- Snake_case for all identifiers
- Private members end with `_`
- Every public method documented in `app.hpp`
- No raw owning pointers — use `std::optional`, `std::vector`

## Adding a feature
1. Add the declaration to `include/luo_gate/app.hpp`
2. Implement in the relevant `src/*.cpp` file
3. Add at least one `CHECK(...)` assertion to `tests/app_tests.cpp`
4. Update `CHANGELOG.md`
5. Open a PR — CI must be green

## Running clang-tidy
```bash
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
clang-tidy -p build src/*.cpp
```
