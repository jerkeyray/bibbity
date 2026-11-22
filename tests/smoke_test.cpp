// Wiring check only: proves GoogleTest is linked and ctest discovers tests.
// Delete once real tests exist.
#include <gtest/gtest.h>

TEST(Smoke, GoogleTestIsWired) { EXPECT_EQ(1 + 1, 2); }
