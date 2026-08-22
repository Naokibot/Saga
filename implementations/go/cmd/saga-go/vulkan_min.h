#ifndef SAGA_VULKAN_MIN_H
#define SAGA_VULKAN_MIN_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif

typedef uint32_t VkFlags; typedef uint32_t VkBool32; typedef uint64_t VkDeviceSize; typedef int32_t VkResult;
typedef int32_t VkStructureType; typedef int32_t VkFormat; typedef int32_t VkColorSpaceKHR; typedef int32_t VkPresentModeKHR; typedef int32_t VkSharingMode; typedef int32_t VkImageLayout; typedef int32_t VkCommandBufferLevel; typedef int32_t VkPhysicalDeviceType;
typedef uint32_t VkQueueFlags; typedef uint32_t VkImageUsageFlags; typedef uint32_t VkMemoryPropertyFlags; typedef uint32_t VkMemoryHeapFlags; typedef uint32_t VkCommandPoolCreateFlags; typedef uint32_t VkCommandBufferUsageFlags; typedef uint32_t VkAccessFlags; typedef uint32_t VkPipelineStageFlags; typedef uint32_t VkImageAspectFlags; typedef uint32_t VkFenceCreateFlags; typedef uint32_t VkCompositeAlphaFlagsKHR; typedef uint32_t VkSurfaceTransformFlagsKHR; typedef uint32_t VkSurfaceTransformFlagBitsKHR; typedef uint32_t VkCompositeAlphaFlagBitsKHR; typedef uint32_t VkBufferUsageFlags; typedef uint32_t VkBufferCreateFlags; typedef uint32_t VkSwapchainCreateFlagsKHR; typedef uint32_t VkDeviceCreateFlags; typedef uint32_t VkDeviceQueueCreateFlags; typedef uint32_t VkInstanceCreateFlags; typedef uint32_t VkSemaphoreCreateFlags; typedef uint32_t VkDependencyFlags; typedef uint32_t VkCommandBufferResetFlags; typedef uint32_t VkMemoryMapFlags;

typedef struct VkInstance_T* VkInstance; typedef struct VkPhysicalDevice_T* VkPhysicalDevice; typedef struct VkDevice_T* VkDevice; typedef struct VkQueue_T* VkQueue; typedef struct VkCommandBuffer_T* VkCommandBuffer;
typedef uint64_t VkSurfaceKHR; typedef uint64_t VkSwapchainKHR; typedef uint64_t VkImage; typedef uint64_t VkBuffer; typedef uint64_t VkDeviceMemory; typedef uint64_t VkCommandPool; typedef uint64_t VkSemaphore; typedef uint64_t VkFence;

#define VK_NULL_HANDLE 0
#define VK_FALSE 0u
#define VK_TRUE 1u
#define VK_SUCCESS 0
#define VK_SUBOPTIMAL_KHR 1000001003
#define VK_ERROR_OUT_OF_DATE_KHR (-1000001004)
#define VK_STRUCTURE_TYPE_APPLICATION_INFO 0
#define VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO 1
#define VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO 2
#define VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO 3
#define VK_STRUCTURE_TYPE_SUBMIT_INFO 4
#define VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO 5
#define VK_STRUCTURE_TYPE_FENCE_CREATE_INFO 8
#define VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO 9
#define VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO 12
#define VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO 39
#define VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO 40
#define VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO 42
#define VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER 45
#define VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR 1000001000
#define VK_STRUCTURE_TYPE_PRESENT_INFO_KHR 1000001001
#define VK_QUEUE_GRAPHICS_BIT 0x00000001u
#define VK_IMAGE_USAGE_TRANSFER_DST_BIT 0x00000002u
#define VK_BUFFER_USAGE_TRANSFER_SRC_BIT 0x00000001u
#define VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT 0x00000002u
#define VK_MEMORY_PROPERTY_HOST_COHERENT_BIT 0x00000004u
#define VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT 0x00000002u
#define VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT 0x00000001u
#define VK_FENCE_CREATE_SIGNALED_BIT 0x00000001u
#define VK_ACCESS_TRANSFER_WRITE_BIT 0x00001000u
#define VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT 0x00000001u
#define VK_PIPELINE_STAGE_TRANSFER_BIT 0x00001000u
#define VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT 0x00002000u
#define VK_IMAGE_ASPECT_COLOR_BIT 0x00000001u
#define VK_IMAGE_LAYOUT_UNDEFINED 0
#define VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL 7
#define VK_IMAGE_LAYOUT_PRESENT_SRC_KHR 1000001002
#define VK_SHARING_MODE_EXCLUSIVE 0
#define VK_COMMAND_BUFFER_LEVEL_PRIMARY 0
#define VK_PRESENT_MODE_FIFO_KHR 2
#define VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR 0x00000001u
#define VK_COMPOSITE_ALPHA_INHERIT_BIT_KHR 0x00000008u
#define VK_FORMAT_R8G8B8A8_UNORM 37
#define VK_FORMAT_R8G8B8A8_SRGB 43
#define VK_FORMAT_B8G8R8A8_UNORM 44
#define VK_FORMAT_B8G8R8A8_SRGB 50
#define VK_QUEUE_FAMILY_IGNORED (~0u)
#define VK_KHR_SWAPCHAIN_EXTENSION_NAME "VK_KHR_swapchain"
#define VK_KHR_PORTABILITY_ENUMERATION_EXTENSION_NAME "VK_KHR_portability_enumeration"
#define VK_KHR_PORTABILITY_SUBSET_EXTENSION_NAME "VK_KHR_portability_subset"
#define VK_INSTANCE_CREATE_ENUMERATE_PORTABILITY_BIT_KHR 0x00000001u
#define VK_KHR_portability_enumeration 1
#define VK_KHR_portability_subset 1
#define VK_MAX_MEMORY_TYPES 32
#define VK_MAX_MEMORY_HEAPS 16
#define VK_MAKE_VERSION(major,minor,patch) ((((uint32_t)(major))<<22)|(((uint32_t)(minor))<<12)|((uint32_t)(patch)))
#define VK_API_VERSION_1_0 VK_MAKE_VERSION(1,0,0)
#define VK_VERSION_MAJOR(version) ((uint32_t)(version)>>22)
#define VK_VERSION_MINOR(version) (((uint32_t)(version)>>12)&0x3ffu)
#define VK_VERSION_PATCH(version) ((uint32_t)(version)&0xfffu)

typedef struct VkExtent2D { uint32_t width,height; } VkExtent2D;
typedef struct VkExtent3D { uint32_t width,height,depth; } VkExtent3D;
typedef struct VkOffset3D { int32_t x,y,z; } VkOffset3D;
typedef struct VkApplicationInfo { VkStructureType sType; const void* pNext; const char* pApplicationName; uint32_t applicationVersion; const char* pEngineName; uint32_t engineVersion; uint32_t apiVersion; } VkApplicationInfo;
typedef struct VkInstanceCreateInfo { VkStructureType sType; const void* pNext; VkInstanceCreateFlags flags; const VkApplicationInfo* pApplicationInfo; uint32_t enabledLayerCount; const char* const* ppEnabledLayerNames; uint32_t enabledExtensionCount; const char* const* ppEnabledExtensionNames; } VkInstanceCreateInfo;
typedef struct VkExtensionProperties { char extensionName[256]; uint32_t specVersion; } VkExtensionProperties;
typedef struct VkQueueFamilyProperties { VkQueueFlags queueFlags; uint32_t queueCount; uint32_t timestampValidBits; VkExtent3D minImageTransferGranularity; } VkQueueFamilyProperties;
typedef struct VkDeviceQueueCreateInfo { VkStructureType sType; const void* pNext; VkDeviceQueueCreateFlags flags; uint32_t queueFamilyIndex; uint32_t queueCount; const float* pQueuePriorities; } VkDeviceQueueCreateInfo;
typedef struct VkPhysicalDeviceFeatures VkPhysicalDeviceFeatures;
typedef struct VkDeviceCreateInfo { VkStructureType sType; const void* pNext; VkDeviceCreateFlags flags; uint32_t queueCreateInfoCount; const VkDeviceQueueCreateInfo* pQueueCreateInfos; uint32_t enabledLayerCount; const char* const* ppEnabledLayerNames; uint32_t enabledExtensionCount; const char* const* ppEnabledExtensionNames; const VkPhysicalDeviceFeatures* pEnabledFeatures; } VkDeviceCreateInfo;
typedef struct VkSurfaceCapabilitiesKHR { uint32_t minImageCount,maxImageCount; VkExtent2D currentExtent,minImageExtent,maxImageExtent; uint32_t maxImageArrayLayers; VkSurfaceTransformFlagsKHR supportedTransforms; VkSurfaceTransformFlagBitsKHR currentTransform; VkCompositeAlphaFlagsKHR supportedCompositeAlpha; VkImageUsageFlags supportedUsageFlags; } VkSurfaceCapabilitiesKHR;
typedef struct VkSurfaceFormatKHR { VkFormat format; VkColorSpaceKHR colorSpace; } VkSurfaceFormatKHR;
typedef struct VkSwapchainCreateInfoKHR { VkStructureType sType; const void* pNext; VkSwapchainCreateFlagsKHR flags; VkSurfaceKHR surface; uint32_t minImageCount; VkFormat imageFormat; VkColorSpaceKHR imageColorSpace; VkExtent2D imageExtent; uint32_t imageArrayLayers; VkImageUsageFlags imageUsage; VkSharingMode imageSharingMode; uint32_t queueFamilyIndexCount; const uint32_t* pQueueFamilyIndices; VkSurfaceTransformFlagBitsKHR preTransform; VkCompositeAlphaFlagBitsKHR compositeAlpha; VkPresentModeKHR presentMode; VkBool32 clipped; VkSwapchainKHR oldSwapchain; } VkSwapchainCreateInfoKHR;
typedef struct VkMemoryType { VkMemoryPropertyFlags propertyFlags; uint32_t heapIndex; } VkMemoryType;
typedef struct VkMemoryHeap { VkDeviceSize size; VkMemoryHeapFlags flags; } VkMemoryHeap;
typedef struct VkPhysicalDeviceMemoryProperties { uint32_t memoryTypeCount; VkMemoryType memoryTypes[VK_MAX_MEMORY_TYPES]; uint32_t memoryHeapCount; VkMemoryHeap memoryHeaps[VK_MAX_MEMORY_HEAPS]; } VkPhysicalDeviceMemoryProperties;
typedef struct VkPhysicalDeviceProperties { uint32_t apiVersion,driverVersion,vendorID,deviceID; VkPhysicalDeviceType deviceType; char deviceName[256]; uint8_t opaque_tail[2048]; } VkPhysicalDeviceProperties;
typedef struct VkBufferCreateInfo { VkStructureType sType; const void* pNext; VkBufferCreateFlags flags; VkDeviceSize size; VkBufferUsageFlags usage; VkSharingMode sharingMode; uint32_t queueFamilyIndexCount; const uint32_t* pQueueFamilyIndices; } VkBufferCreateInfo;
typedef struct VkMemoryRequirements { VkDeviceSize size; VkDeviceSize alignment; uint32_t memoryTypeBits; } VkMemoryRequirements;
typedef struct VkMemoryAllocateInfo { VkStructureType sType; const void* pNext; VkDeviceSize allocationSize; uint32_t memoryTypeIndex; } VkMemoryAllocateInfo;
typedef struct VkCommandPoolCreateInfo { VkStructureType sType; const void* pNext; VkCommandPoolCreateFlags flags; uint32_t queueFamilyIndex; } VkCommandPoolCreateInfo;
typedef struct VkCommandBufferAllocateInfo { VkStructureType sType; const void* pNext; VkCommandPool commandPool; VkCommandBufferLevel level; uint32_t commandBufferCount; } VkCommandBufferAllocateInfo;
typedef struct VkSemaphoreCreateInfo { VkStructureType sType; const void* pNext; VkSemaphoreCreateFlags flags; } VkSemaphoreCreateInfo;
typedef struct VkFenceCreateInfo { VkStructureType sType; const void* pNext; VkFenceCreateFlags flags; } VkFenceCreateInfo;
typedef struct VkCommandBufferInheritanceInfo VkCommandBufferInheritanceInfo;
typedef struct VkCommandBufferBeginInfo { VkStructureType sType; const void* pNext; VkCommandBufferUsageFlags flags; const VkCommandBufferInheritanceInfo* pInheritanceInfo; } VkCommandBufferBeginInfo;
typedef struct VkImageSubresourceRange { VkImageAspectFlags aspectMask; uint32_t baseMipLevel,levelCount,baseArrayLayer,layerCount; } VkImageSubresourceRange;
typedef struct VkImageMemoryBarrier { VkStructureType sType; const void* pNext; VkAccessFlags srcAccessMask,dstAccessMask; VkImageLayout oldLayout,newLayout; uint32_t srcQueueFamilyIndex,dstQueueFamilyIndex; VkImage image; VkImageSubresourceRange subresourceRange; } VkImageMemoryBarrier;
typedef struct VkImageSubresourceLayers { VkImageAspectFlags aspectMask; uint32_t mipLevel,baseArrayLayer,layerCount; } VkImageSubresourceLayers;
typedef struct VkBufferImageCopy { VkDeviceSize bufferOffset; uint32_t bufferRowLength,bufferImageHeight; VkImageSubresourceLayers imageSubresource; VkOffset3D imageOffset; VkExtent3D imageExtent; } VkBufferImageCopy;
typedef struct VkSubmitInfo { VkStructureType sType; const void* pNext; uint32_t waitSemaphoreCount; const VkSemaphore* pWaitSemaphores; const VkPipelineStageFlags* pWaitDstStageMask; uint32_t commandBufferCount; const VkCommandBuffer* pCommandBuffers; uint32_t signalSemaphoreCount; const VkSemaphore* pSignalSemaphores; } VkSubmitInfo;
typedef struct VkPresentInfoKHR { VkStructureType sType; const void* pNext; uint32_t waitSemaphoreCount; const VkSemaphore* pWaitSemaphores; uint32_t swapchainCount; const VkSwapchainKHR* pSwapchains; const uint32_t* pImageIndices; VkResult* pResults; } VkPresentInfoKHR;

VkResult vkEnumerateInstanceExtensionProperties(const char*,uint32_t*,VkExtensionProperties*);
VkResult vkCreateInstance(const VkInstanceCreateInfo*,const void*,VkInstance*); void vkDestroyInstance(VkInstance,const void*);
VkResult vkEnumeratePhysicalDevices(VkInstance,uint32_t*,VkPhysicalDevice*); void vkGetPhysicalDeviceProperties(VkPhysicalDevice,VkPhysicalDeviceProperties*); void vkGetPhysicalDeviceQueueFamilyProperties(VkPhysicalDevice,uint32_t*,VkQueueFamilyProperties*); void vkGetPhysicalDeviceMemoryProperties(VkPhysicalDevice,VkPhysicalDeviceMemoryProperties*);
VkResult vkEnumerateDeviceExtensionProperties(VkPhysicalDevice,const char*,uint32_t*,VkExtensionProperties*);
VkResult vkGetPhysicalDeviceSurfaceSupportKHR(VkPhysicalDevice,uint32_t,VkSurfaceKHR,VkBool32*); VkResult vkGetPhysicalDeviceSurfaceCapabilitiesKHR(VkPhysicalDevice,VkSurfaceKHR,VkSurfaceCapabilitiesKHR*); VkResult vkGetPhysicalDeviceSurfaceFormatsKHR(VkPhysicalDevice,VkSurfaceKHR,uint32_t*,VkSurfaceFormatKHR*); void vkDestroySurfaceKHR(VkInstance,VkSurfaceKHR,const void*);
VkResult vkCreateDevice(VkPhysicalDevice,const VkDeviceCreateInfo*,const void*,VkDevice*); void vkDestroyDevice(VkDevice,const void*); void vkGetDeviceQueue(VkDevice,uint32_t,uint32_t,VkQueue*); VkResult vkDeviceWaitIdle(VkDevice);
VkResult vkCreateSwapchainKHR(VkDevice,const VkSwapchainCreateInfoKHR*,const void*,VkSwapchainKHR*); void vkDestroySwapchainKHR(VkDevice,VkSwapchainKHR,const void*); VkResult vkGetSwapchainImagesKHR(VkDevice,VkSwapchainKHR,uint32_t*,VkImage*); VkResult vkAcquireNextImageKHR(VkDevice,VkSwapchainKHR,uint64_t,VkSemaphore,VkFence,uint32_t*); VkResult vkQueuePresentKHR(VkQueue,const VkPresentInfoKHR*);
VkResult vkCreateBuffer(VkDevice,const VkBufferCreateInfo*,const void*,VkBuffer*); void vkDestroyBuffer(VkDevice,VkBuffer,const void*); void vkGetBufferMemoryRequirements(VkDevice,VkBuffer,VkMemoryRequirements*); VkResult vkAllocateMemory(VkDevice,const VkMemoryAllocateInfo*,const void*,VkDeviceMemory*); void vkFreeMemory(VkDevice,VkDeviceMemory,const void*); VkResult vkBindBufferMemory(VkDevice,VkBuffer,VkDeviceMemory,VkDeviceSize); VkResult vkMapMemory(VkDevice,VkDeviceMemory,VkDeviceSize,VkDeviceSize,VkMemoryMapFlags,void**); void vkUnmapMemory(VkDevice,VkDeviceMemory);
VkResult vkCreateCommandPool(VkDevice,const VkCommandPoolCreateInfo*,const void*,VkCommandPool*); void vkDestroyCommandPool(VkDevice,VkCommandPool,const void*); VkResult vkAllocateCommandBuffers(VkDevice,const VkCommandBufferAllocateInfo*,VkCommandBuffer*); VkResult vkResetCommandBuffer(VkCommandBuffer,VkCommandBufferResetFlags); VkResult vkBeginCommandBuffer(VkCommandBuffer,const VkCommandBufferBeginInfo*); VkResult vkEndCommandBuffer(VkCommandBuffer);
VkResult vkCreateSemaphore(VkDevice,const VkSemaphoreCreateInfo*,const void*,VkSemaphore*); void vkDestroySemaphore(VkDevice,VkSemaphore,const void*); VkResult vkCreateFence(VkDevice,const VkFenceCreateInfo*,const void*,VkFence*); void vkDestroyFence(VkDevice,VkFence,const void*); VkResult vkWaitForFences(VkDevice,uint32_t,const VkFence*,VkBool32,uint64_t); VkResult vkResetFences(VkDevice,uint32_t,const VkFence*);
void vkCmdPipelineBarrier(VkCommandBuffer,VkPipelineStageFlags,VkPipelineStageFlags,VkDependencyFlags,uint32_t,const void*,uint32_t,const void*,uint32_t,const VkImageMemoryBarrier*); void vkCmdCopyBufferToImage(VkCommandBuffer,VkBuffer,VkImage,VkImageLayout,uint32_t,const VkBufferImageCopy*); VkResult vkQueueSubmit(VkQueue,uint32_t,const VkSubmitInfo*,VkFence);

#ifdef __cplusplus
}
#endif
#endif
