//go:build windows

package main

import (
	"fmt"
	"syscall"
	"unsafe"
)

var sagaMoveFileExW = syscall.NewLazyDLL("kernel32.dll").NewProc("MoveFileExW")

const (
	sagaMoveFileReplaceExisting = 0x00000001
	sagaMoveFileWriteThrough    = 0x00000008
)

func atomicReplacePath(oldPath, newPath string) error {
	oldPtr, err := syscall.UTF16PtrFromString(oldPath)
	if err != nil {
		return err
	}
	newPtr, err := syscall.UTF16PtrFromString(newPath)
	if err != nil {
		return err
	}
	r1, _, callErr := sagaMoveFileExW.Call(
		uintptr(unsafe.Pointer(oldPtr)),
		uintptr(unsafe.Pointer(newPtr)),
		uintptr(sagaMoveFileReplaceExisting|sagaMoveFileWriteThrough),
	)
	if r1 == 0 {
		return fmt.Errorf("MoveFileExW: %v", callErr)
	}
	return nil
}
