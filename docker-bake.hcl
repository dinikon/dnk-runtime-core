variable "REGISTRY_PREFIX" {
  default = "ghcr.io/dinikon/runtime"
}

variable "VERSION" {
  default = "0.1.0"
}

variable "IMAGE_TAG" {
  default = "local"
}

variable "SOURCE_URL" {
  default = "https://github.com/dinikon/dnk-runtime-core"
}

variable "SOURCE_REVISION" {
  default = ""
}

variable "PLATFORMS" {
  default = "linux/amd64,linux/arm64"
}

group "default" {
  targets = ["runtime", "frontend-runtime"]
}

target "_common" {
  platforms = split(",", PLATFORMS)
  annotations = [
    "index:org.opencontainers.image.source=${SOURCE_URL}",
    "index:org.opencontainers.image.version=${VERSION}",
    "index:org.opencontainers.image.revision=${SOURCE_REVISION}"
  ]
  labels = {
    "org.opencontainers.image.source" = SOURCE_URL
    "org.opencontainers.image.version" = VERSION
    "org.opencontainers.image.revision" = SOURCE_REVISION
  }
}


target "runtime" {
  inherits = ["_common"]
  context = "."
  dockerfile = "Dockerfile"
  target = "runtime"
  tags = ["${REGISTRY_PREFIX}/runtime:${IMAGE_TAG}"]
  labels = {
    "org.opencontainers.image.title" = "runtime"
    "org.opencontainers.image.description" = "FastAPI tenant runtime API and workers"
  }
}


target "frontend-runtime" {
  inherits = ["_common"]
  context = "frontends"
  dockerfile = "Dockerfile"
  target = "runtime"
  tags = ["${REGISTRY_PREFIX}/frontend-runtime:${IMAGE_TAG}"]
  labels = {
    "org.opencontainers.image.title" = "frontend-runtime"
    "org.opencontainers.image.description" = "Runtime Vue console served by Nginx"
  }
}
