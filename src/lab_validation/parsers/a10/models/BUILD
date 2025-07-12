load("@rules_python//python:defs.bzl", "py_library")
load("@pip//:requirements.bzl", "requirement")
load("//starlark/pytest:pytest.bzl", "py_pytest_test")

py_library(
    name = "routes",
    srcs = ["routes.py"],
    visibility = ["//validation:__subpackages__"],
    deps = [
        requirement("attrs"),
        ":util",
        "//validation/showparser_v2/common",
    ],
)

py_library(
    name = "bgp",
    srcs = ["bgp.py"],
    visibility = ["//validation:__subpackages__"],
    deps = [
        requirement("attrs"),
        ":util",
        "//validation/showparser_v2/common",
    ],
)

py_library(
    name = "util",
    srcs = ["util.py"],
)

py_pytest_test(
    name = "util_test",
    srcs = ["util_test.py"],
    deps = [":util"],
)
