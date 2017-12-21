package(default_visibility = ["//visibility:public"])

load("@hello_initializers_pip//:requirements.bzl", "requirement")
load("@io_bazel_rules_docker//python:image.bzl", "py_image")

py_image(
    name = "controller",
    srcs = ["controller.py"],
    main = "controller.py",
    deps = [requirement("kubernetes")],
)

load("@k8s_initializerconfiguration//:defaults.bzl", "k8s_initializerconfiguration")

k8s_initializerconfiguration(
    name = "inicfg",
    template = ":init.yaml",
)

load("@k8s_deployment//:defaults.bzl", "k8s_deployment")

k8s_deployment(
    name = "deployment",
    images = {
        "gcr.io/convoy-adapter/hello-initializers/controller:latest": ":controller",
    },
    template = ":controller.yaml",
)

load("@k8s_object//:defaults.bzl", "k8s_object")

k8s_object(
    name = "example",
    template = ":example-job.yaml",
)
