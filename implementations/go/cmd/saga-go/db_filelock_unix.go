//go:build !windows

package main

import (
	"os"
	"path/filepath"
	"strconv"
	"syscall"
)

func kvLockFilePath(path string) string {
	base, err := os.UserCacheDir()
	if err != nil || base == "" {
		base = filepath.Join(os.TempDir(), "saga-"+strconv.Itoa(os.Getuid()))
	}
	return filepath.Join(base, "Saga", "kv-locks", filepath.Base(canonicalDBLockIdentity(path))+"-"+safeLockIdentity(canonicalDBLockIdentity(path))+".lock")
}

func withKVFileLock(path string, exclusive bool, fn func() error) error {
	lockPath := kvLockFilePath(path)
	if err := os.MkdirAll(filepath.Dir(lockPath), 0700); err != nil {
		return err
	}
	f, err := os.OpenFile(lockPath, os.O_CREATE|os.O_RDWR, 0600)
	if err != nil {
		return err
	}
	defer f.Close()
	how := syscall.LOCK_SH
	if exclusive {
		how = syscall.LOCK_EX
	}
	if err := syscall.Flock(int(f.Fd()), how); err != nil {
		return err
	}
	defer syscall.Flock(int(f.Fd()), syscall.LOCK_UN)
	return fn()
}
