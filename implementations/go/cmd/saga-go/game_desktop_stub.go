//go:build !sagadesktop || !cgo

package main

import "fmt"

func desktopAvailable() bool     { return false }
func desktopBackendName() string { return "unavailable" }
func desktopOpenWindow(title string, w, h int) (uintptr, error) {
	return 0, fmt.Errorf("desktop game backend unavailable; Linux builds can enable -tags sagadesktop")
}
func desktopCloseWindow(h uintptr) {}
func desktopPoll(h uintptr) (bool, error) {
	return false, fmt.Errorf("desktop game backend unavailable")
}
func desktopKeyDown(h uintptr, key string) (bool, error) {
	return false, fmt.Errorf("desktop game backend unavailable")
}
func desktopMouse(h uintptr) (int, int, uint32, error) {
	return 0, 0, 0, fmt.Errorf("desktop game backend unavailable")
}
func desktopGamepadCount() int { return 0 }
func desktopOpenGamepad(index int) (uintptr, error) {
	return 0, fmt.Errorf("desktop game backend unavailable")
}
func desktopCloseGamepad(h uintptr) {}
func desktopGamepadButton(h uintptr, button string) (bool, error) {
	return false, fmt.Errorf("desktop game backend unavailable")
}
func desktopGamepadAxis(h uintptr, axis string) (float64, error) {
	return 0, fmt.Errorf("desktop game backend unavailable")
}
func desktopRendererCreate(window uintptr) (uintptr, string, error) {
	return 0, "", fmt.Errorf("desktop game backend unavailable")
}
func desktopRendererDestroy(h uintptr) {}
func desktopRenderer2DCreate(window uintptr, requested string) (uintptr, string, error) {
	return 0, "", fmt.Errorf("desktop game backend unavailable")
}
func desktopRenderer2DDestroy(h uintptr) {}
func desktopRenderer2DPresent(h uintptr, rgba []byte, w, hgt int) error {
	return fmt.Errorf("desktop game backend unavailable")
}
func desktopRendererDrivers() string     { return "" }
func desktopVulkanProbe() (bool, string) { return false, "Vulkan probe unavailable" }
func desktopShaderCreate(renderer uintptr, fragment string) (uintptr, error) {
	return 0, fmt.Errorf("desktop game backend unavailable")
}
func desktopShaderProgramCreate(renderer uintptr, vertex, fragment string) (uintptr, error) {
	return 0, fmt.Errorf("desktop game backend unavailable")
}
func desktopShaderDestroy(renderer, shader uintptr) {}
func desktopRendererPresent(renderer uintptr, rgba []byte, w, h int, shader uintptr) error {
	return fmt.Errorf("desktop game backend unavailable")
}
func desktopAudioPlay(pcm []byte, rate, channels int) error {
	return fmt.Errorf("desktop game backend unavailable")
}
