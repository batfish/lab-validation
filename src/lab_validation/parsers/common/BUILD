load("@rules_python//python:defs.bzl", "py_library")
load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "common",
    srcs = glob(["*.py"]),
    visibility = ["//validation:__subpackages__"],
    deps = [requirement("pyparsing")],
)
