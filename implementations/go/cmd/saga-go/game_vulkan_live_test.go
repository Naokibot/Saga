//go:build linux && sagadesktop && sagavulkan && cgo

package main

import (
	"os"
	"strings"
	"testing"
)

// TestDesktopVulkanSwapchainPresent is an opt-in qualification test. It executes
// the production Vulkan renderer all the way through instance/device/surface,
// swapchain acquisition, command submission and vkQueuePresentKHR. It is kept
// opt-in because ordinary unit-test hosts are not required to expose a Vulkan ICD
// or display server.
func TestDesktopVulkanSwapchainPresent(t *testing.T) {
	if os.Getenv("SAGA_VULKAN_LIVE") != "1" {
		t.Skip("set SAGA_VULKAN_LIVE=1 with a display server and Vulkan ICD")
	}
	const width, height = 128, 96
	old, err := desktopOpenWindow("Saga Vulkan bootstrap", width, height)
	if err != nil {
		t.Fatal(err)
	}
	renderer, window, info, err := desktopVulkanRendererCreate(old, "Saga Vulkan qualification", width, height)
	if err != nil {
		desktopCloseWindow(old)
		t.Fatal(err)
	}
	defer desktopVulkanRendererDestroy(renderer)
	defer desktopCloseWindow(window)
	if !strings.Contains(info, "Vulkan device=") || !strings.Contains(info, "swapchain=") {
		t.Fatalf("missing Vulkan qualification evidence: %q", info)
	}
	frame := make([]byte, width*height*4)
	for y := 0; y < height; y++ {
		for x := 0; x < width; x++ {
			i := (y*width + x) * 4
			frame[i+0] = byte((x * 255) / (width - 1))
			frame[i+1] = byte((y * 255) / (height - 1))
			frame[i+2] = 96
			frame[i+3] = 255
		}
	}
	if err := desktopVulkanRendererPresent(renderer, frame, width, height); err != nil {
		t.Fatal(err)
	}
	frame[0], frame[1], frame[2] = 255, 255, 255
	if err := desktopVulkanRendererPresent(renderer, frame, width, height); err != nil {
		t.Fatal(err)
	}
	t.Log(info)
}
