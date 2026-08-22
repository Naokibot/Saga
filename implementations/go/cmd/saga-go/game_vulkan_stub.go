//go:build !sagavulkan || !sagadesktop || !cgo

package main

import "fmt"

func desktopVulkanRendererCompiled() bool { return false }
func desktopVulkanRendererCreate(oldWindow uintptr, title string, width, height int) (renderer uintptr, newWindow uintptr, info string, err error) {
	return 0, oldWindow, "", fmt.Errorf("Vulkan presentation backend is not compiled; rebuild with -tags 'sagadesktop sagavulkan' and a Vulkan SDK")
}
func desktopVulkanRendererDestroy(handle uintptr) {}
func desktopVulkanRendererPresent(handle uintptr, rgba []byte, width, height int) error {
	return fmt.Errorf("Vulkan presentation backend is not compiled")
}
