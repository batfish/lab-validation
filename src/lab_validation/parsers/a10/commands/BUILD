load("@rules_python//python:defs.bzl", "py_library")
load("@pip//:requirements.bzl", "requirement")
load("//starlark/pytest:pytest.bzl", "py_pytest_test")

py_library(
    name = "bgp",
    srcs = ["bgp.py"],
    visibility = ["//validation:__subpackages__"],
    deps = [
        requirement("attrs"),
        requirement("pyparsing"),
        "//validation/showparser_v2/a10/models:bgp",
        "//validation/showparser_v2/common",
    ],
)

py_pytest_test(
    name = "bgp_test",
    srcs = ["bgp_test.py"],
    deps = [":bgp"],
)

py_library(
    name = "routes",
    srcs = ["routes.py"],
    visibility = ["//validation:__subpackages__"],
    deps = [
        requirement("attrs"),
        requirement("pyparsing"),
        "//validation/showparser_v2/a10/models:routes",
        "//validation/showparser_v2/common",
    ],
)

py_pytest_test(
    name = "routes_test",
    srcs = ["routes_test.py"],
    deps = [":routes"],
)
