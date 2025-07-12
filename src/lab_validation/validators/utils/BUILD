load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "utils",
    srcs = ["validation_utils.py"],
    visibility = [
        "//validation:__subpackages__",
    ],
    deps = [
        "//validation/lab_validation/vendor_validators/batfish_models",
    ],
)
