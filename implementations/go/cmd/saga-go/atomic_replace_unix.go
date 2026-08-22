//go:build !windows

package main

import "os"

func atomicReplacePath(oldPath, newPath string) error {
	return os.Rename(oldPath, newPath)
}
