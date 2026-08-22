//go:build windows

package main

import (
	"fmt"
	"os"
	"path/filepath"
	"syscall"
	"unsafe"
)

var (
	sagaKernel32     = syscall.NewLazyDLL("kernel32.dll")
	sagaLockFileEx   = sagaKernel32.NewProc("LockFileEx")
	sagaUnlockFileEx = sagaKernel32.NewProc("UnlockFileEx")
)

const sagaLockfileExclusiveLock = 0x00000002

func kvLockFilePath(path string) string {
	base, err := os.UserCacheDir()
	if err != nil || base == "" {
		base = os.TempDir()
	}
	return filepath.Join(base, "Saga", "kv-locks", safeLockIdentity(canonicalDBLockIdentity(path))+".lock")
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
	var ol syscall.Overlapped
	flags := uintptr(0)
	if exclusive {
		flags = sagaLockfileExclusiveLock
	}
	r1, _, callErr := sagaLockFileEx.Call(f.Fd(), flags, 0, 1, 0, uintptr(unsafe.Pointer(&ol)))
	if r1 == 0 {
		return fmt.Errorf("LockFileEx: %v", callErr)
	}
	defer sagaUnlockFileEx.Call(f.Fd(), 0, 1, 0, uintptr(unsafe.Pointer(&ol)))
	return fn()
}
