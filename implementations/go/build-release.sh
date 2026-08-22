#!/bin/sh
set -eu
mkdir -p bin
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags='-s -w' -o bin/saga-go-linux-amd64 ./cmd/saga-go
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -trimpath -ldflags='-s -w' -o bin/saga-go-linux-arm64 ./cmd/saga-go
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -trimpath -ldflags='-s -w' -o bin/saga-go-windows-amd64.exe ./cmd/saga-go
CGO_ENABLED=0 GOOS=windows GOARCH=arm64 go build -trimpath -ldflags='-s -w' -o bin/saga-go-windows-arm64.exe ./cmd/saga-go
