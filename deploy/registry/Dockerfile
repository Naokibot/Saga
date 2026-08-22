FROM golang:1.23-bookworm AS build
WORKDIR /src
COPY implementations/go/ ./implementations/go/
WORKDIR /src/implementations/go
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/saga ./cmd/saga-go

FROM debian:13-slim
RUN useradd --system --uid 10001 --create-home saga \
    && mkdir -p /var/lib/saga-registry \
    && chown -R saga:saga /var/lib/saga-registry
COPY --from=build /out/saga /usr/local/bin/saga
USER saga
VOLUME ["/var/lib/saga-registry"]
EXPOSE 7331
ENTRYPOINT ["/usr/local/bin/saga","registry","serve","--root","/var/lib/saga-registry","--addr","0.0.0.0:7331"]
