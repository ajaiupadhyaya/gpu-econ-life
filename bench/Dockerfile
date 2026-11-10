# P1 benchmark image. Build from the REPO ROOT (it copies bench/ and config/bench.yaml):
#
#   docker buildx build --platform linux/amd64 -f bench/Dockerfile \
#     --build-arg BENCH_GIT_COMMIT=$(git rev-parse HEAD) -t <namespace>/gel-bench:v0.32.0 --push .
#
# Runpod hosts are x86_64, so --platform linux/amd64 is required on Apple Silicon.
# A non-Runpod base image must start sshd itself from PUBLIC_KEY, or scp is impossible
# (docs.runpod.io/pods/configuration/use-ssh). Expose 22/tcp in the Runpod template.
FROM vllm/vllm-openai:v0.32.0

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends openssh-server tmux \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /run/sshd

ARG BENCH_GIT_COMMIT=unknown
ENV BENCH_GIT_COMMIT=${BENCH_GIT_COMMIT} \
    TZ=UTC \
    PYTHONUNBUFFERED=1

WORKDIR /opt/gel
COPY bench/ /opt/gel/bench/
COPY config/bench.yaml /opt/gel/config/bench.yaml
RUN chmod +x /opt/gel/bench/*.sh /opt/gel/bench/*.py /opt/gel/bench/pod_start.sh \
 && rm -rf /opt/gel/bench/stubs   # stubs never ship to a real GPU

ENTRYPOINT ["/opt/gel/bench/pod_start.sh"]
