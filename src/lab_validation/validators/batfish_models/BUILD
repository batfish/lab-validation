load("@rules_python//python:defs.bzl", "py_library")
load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "batfish_models",
    srcs = [
        "interface_properties.py",
        "routes.py",
        "runtime_data.py",
    ],
    visibility = ["//validation:__subpackages__"],
    deps = [
        "//validation/showparser_v2/common",
        requirement("attrs"),
        requirement("pybatfish"),
    ],
)
