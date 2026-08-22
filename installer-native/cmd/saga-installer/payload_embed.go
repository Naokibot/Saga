//go:build saga_installer_payload

package main

import (
	"embed"
	"io/fs"
)

// The release builder populates payload/ immediately before compiling the
// offline installer. The build tag prevents source-only distributions from
// requiring generated binaries merely to compile or run tests.
//
//go:embed payload/*
var embeddedPayload embed.FS

var payload fs.FS = embeddedPayload
