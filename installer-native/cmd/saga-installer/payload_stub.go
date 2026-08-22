//go:build !saga_installer_payload

package main

import "io/fs"

type emptyPayloadFS struct{}

func (emptyPayloadFS) Open(name string) (fs.File, error) {
	return nil, &fs.PathError{Op: "open", Path: name, Err: fs.ErrNotExist}
}

// Source distributions intentionally omit generated native payload binaries.
// Official installers replace this empty FS at build time via the
// saga_installer_payload build tag.
var payload fs.FS = emptyPayloadFS{}
