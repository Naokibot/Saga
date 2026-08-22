//go:build sagavulkan && sagadesktop && cgo

package main

/*
#cgo CFLAGS: -I${SRCDIR}
#cgo linux LDFLAGS: -l:libSDL2-2.0.so.0 -l:libvulkan.so.1
#cgo windows LDFLAGS: -lSDL2 -lvulkan-1
#cgo darwin LDFLAGS: -lSDL2 -lvulkan
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "vulkan_min.h"

typedef struct SDL_Window SDL_Window;
extern int SDL_InitSubSystem(uint32_t flags);
extern uint32_t SDL_WasInit(uint32_t flags);
extern const char* SDL_GetError(void);
extern SDL_Window* SDL_CreateWindow(const char*, int, int, int, int, uint32_t);
extern void SDL_DestroyWindow(SDL_Window*);
extern int SDL_Vulkan_GetInstanceExtensions(SDL_Window*, unsigned int*, const char**);
extern int SDL_Vulkan_CreateSurface(SDL_Window*, VkInstance, VkSurfaceKHR*);

#define SAGA_SDL_INIT_VIDEO 0x00000020u
#define SAGA_SDL_WINDOWPOS_CENTERED 0x2FFF0000u
#define SAGA_SDL_WINDOW_SHOWN 0x00000004u
#define SAGA_SDL_WINDOW_RESIZABLE 0x00000020u
#define SAGA_SDL_WINDOW_VULKAN 0x10000000u

typedef struct SagaVkRenderer {
    SDL_Window* window;
    VkInstance instance;
    VkSurfaceKHR surface;
    VkPhysicalDevice physical;
    VkDevice device;
    uint32_t queue_family;
    VkQueue queue;
    VkSwapchainKHR swapchain;
    VkFormat format;
    VkExtent2D extent;
    uint32_t image_count;
    VkImage* images;
    VkCommandPool command_pool;
    VkCommandBuffer command;
    VkSemaphore image_available;
    VkSemaphore render_finished;
    VkFence fence;
    VkBuffer staging;
    VkDeviceMemory staging_memory;
    VkDeviceSize staging_size;
    int bgra;
    char info[1024];
} SagaVkRenderer;

static char saga_vk_error[2048];
static void saga_vk_set_error(const char* text) {
    if (!text) text = "Vulkan error";
    snprintf(saga_vk_error, sizeof(saga_vk_error), "%s", text);
}
static void saga_vk_set_result(const char* where, VkResult r) {
    snprintf(saga_vk_error, sizeof(saga_vk_error), "%s failed (VkResult=%d)", where, (int)r);
}
static const char* saga_vk_last_error(void) { return saga_vk_error; }

static uint32_t saga_vk_choose_memory(VkPhysicalDevice physical, uint32_t bits, VkMemoryPropertyFlags flags) {
    VkPhysicalDeviceMemoryProperties props;
    vkGetPhysicalDeviceMemoryProperties(physical, &props);
    for (uint32_t i=0; i<props.memoryTypeCount; ++i) {
        if ((bits & (1u<<i)) && (props.memoryTypes[i].propertyFlags & flags) == flags) return i;
    }
    return UINT32_MAX;
}

static int saga_vk_has_device_extension(VkPhysicalDevice physical, const char* name) {
    uint32_t count=0;
    if (vkEnumerateDeviceExtensionProperties(physical, NULL, &count, NULL) != VK_SUCCESS) return 0;
    if (!count) return 0;
    VkExtensionProperties* p=(VkExtensionProperties*)calloc(count,sizeof(VkExtensionProperties));
    if (!p) return 0;
    int found=0;
    if (vkEnumerateDeviceExtensionProperties(physical,NULL,&count,p)==VK_SUCCESS) {
        for(uint32_t i=0;i<count;i++) if(strcmp(p[i].extensionName,name)==0){found=1;break;}
    }
    free(p); return found;
}

static void saga_vk_renderer_destroy(SagaVkRenderer* r) {
    if (!r) return;
    if (r->device) vkDeviceWaitIdle(r->device);
    if (r->device && r->fence) vkDestroyFence(r->device,r->fence,NULL);
    if (r->device && r->render_finished) vkDestroySemaphore(r->device,r->render_finished,NULL);
    if (r->device && r->image_available) vkDestroySemaphore(r->device,r->image_available,NULL);
    if (r->device && r->staging) vkDestroyBuffer(r->device,r->staging,NULL);
    if (r->device && r->staging_memory) vkFreeMemory(r->device,r->staging_memory,NULL);
    if (r->device && r->command_pool) vkDestroyCommandPool(r->device,r->command_pool,NULL);
    if (r->device && r->swapchain) vkDestroySwapchainKHR(r->device,r->swapchain,NULL);
    free(r->images);
    if (r->device) vkDestroyDevice(r->device,NULL);
    if (r->instance && r->surface) vkDestroySurfaceKHR(r->instance,r->surface,NULL);
    if (r->instance) vkDestroyInstance(r->instance,NULL);
    free(r);
}

static SagaVkRenderer* saga_vk_renderer_create(uintptr_t old_window, const char* title, int width, int height, uintptr_t* out_window, char* out_info, size_t out_cap) {
    if (out_window) *out_window=old_window;
    if (!title || width<=0 || height<=0) { saga_vk_set_error("invalid Vulkan window arguments"); return NULL; }
    if (!(SDL_WasInit(SAGA_SDL_INIT_VIDEO)&SAGA_SDL_INIT_VIDEO) && SDL_InitSubSystem(SAGA_SDL_INIT_VIDEO)!=0) {
        saga_vk_set_error(SDL_GetError()); return NULL;
    }
    SDL_Window* window=SDL_CreateWindow(title,(int)SAGA_SDL_WINDOWPOS_CENTERED,(int)SAGA_SDL_WINDOWPOS_CENTERED,width,height,
        SAGA_SDL_WINDOW_VULKAN|SAGA_SDL_WINDOW_SHOWN|SAGA_SDL_WINDOW_RESIZABLE);
    if (!window) { saga_vk_set_error(SDL_GetError()); return NULL; }
    SagaVkRenderer* r=(SagaVkRenderer*)calloc(1,sizeof(SagaVkRenderer));
    if(!r){SDL_DestroyWindow(window);saga_vk_set_error("out of memory");return NULL;}
    r->window=window;

    unsigned int ext_count=0;
    if(!SDL_Vulkan_GetInstanceExtensions(window,&ext_count,NULL)||ext_count==0){saga_vk_set_error(SDL_GetError());goto fail;}
    const char** exts=(const char**)calloc(ext_count+1,sizeof(char*));
    if(!exts){saga_vk_set_error("out of memory");goto fail;}
    if(!SDL_Vulkan_GetInstanceExtensions(window,&ext_count,exts)){free(exts);saga_vk_set_error(SDL_GetError());goto fail;}

    VkApplicationInfo app={0}; app.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO; app.pApplicationName="Saga"; app.applicationVersion=VK_MAKE_VERSION(0,17,0); app.pEngineName="Saga Vulkan"; app.engineVersion=VK_MAKE_VERSION(0,17,0); app.apiVersion=VK_API_VERSION_1_0;
    VkInstanceCreateInfo ici={0}; ici.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO; ici.pApplicationInfo=&app; ici.enabledExtensionCount=ext_count; ici.ppEnabledExtensionNames=exts;
#ifdef VK_KHR_portability_enumeration
    int portability_instance=0;
    uint32_t iec=0;
    if(vkEnumerateInstanceExtensionProperties(NULL,&iec,NULL)==VK_SUCCESS && iec){
        VkExtensionProperties* ie=(VkExtensionProperties*)calloc(iec,sizeof(VkExtensionProperties));
        if(ie && vkEnumerateInstanceExtensionProperties(NULL,&iec,ie)==VK_SUCCESS){for(uint32_t i=0;i<iec;i++)if(strcmp(ie[i].extensionName,VK_KHR_PORTABILITY_ENUMERATION_EXTENSION_NAME)==0)portability_instance=1;}
        free(ie);
    }
    if(portability_instance){ exts[ext_count++]=VK_KHR_PORTABILITY_ENUMERATION_EXTENSION_NAME; ici.enabledExtensionCount=ext_count; ici.flags|=VK_INSTANCE_CREATE_ENUMERATE_PORTABILITY_BIT_KHR; }
#endif
    VkResult vr=vkCreateInstance(&ici,NULL,&r->instance); free(exts); if(vr!=VK_SUCCESS){saga_vk_set_result("vkCreateInstance",vr);goto fail;}
    if(!SDL_Vulkan_CreateSurface(window,r->instance,&r->surface)){saga_vk_set_error(SDL_GetError());goto fail;}

    uint32_t pc=0; vr=vkEnumeratePhysicalDevices(r->instance,&pc,NULL); if(vr!=VK_SUCCESS||pc==0){saga_vk_set_result("vkEnumeratePhysicalDevices",vr);goto fail;}
    VkPhysicalDevice* phys=(VkPhysicalDevice*)calloc(pc,sizeof(VkPhysicalDevice)); if(!phys){saga_vk_set_error("out of memory");goto fail;}
    vr=vkEnumeratePhysicalDevices(r->instance,&pc,phys); if(vr!=VK_SUCCESS){free(phys);saga_vk_set_result("vkEnumeratePhysicalDevices",vr);goto fail;}
    int found=0;
    for(uint32_t pi=0;pi<pc&&!found;pi++){
        uint32_t qc=0;vkGetPhysicalDeviceQueueFamilyProperties(phys[pi],&qc,NULL);if(!qc)continue;
        VkQueueFamilyProperties* qp=(VkQueueFamilyProperties*)calloc(qc,sizeof(VkQueueFamilyProperties));if(!qp)continue;vkGetPhysicalDeviceQueueFamilyProperties(phys[pi],&qc,qp);
        for(uint32_t qi=0;qi<qc;qi++){
            VkBool32 present=VK_FALSE;vkGetPhysicalDeviceSurfaceSupportKHR(phys[pi],qi,r->surface,&present);
            if((qp[qi].queueFlags&VK_QUEUE_GRAPHICS_BIT)&&present&&saga_vk_has_device_extension(phys[pi],VK_KHR_SWAPCHAIN_EXTENSION_NAME)){r->physical=phys[pi];r->queue_family=qi;found=1;break;}
        }
        free(qp);
    }
    free(phys);if(!found){saga_vk_set_error("no Vulkan physical device with graphics+present+VK_KHR_swapchain");goto fail;}

    float priority=1.0f;VkDeviceQueueCreateInfo qci={0};qci.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;qci.queueFamilyIndex=r->queue_family;qci.queueCount=1;qci.pQueuePriorities=&priority;
    const char* dev_exts[2]={VK_KHR_SWAPCHAIN_EXTENSION_NAME,NULL};uint32_t dev_ext_count=1;
#ifdef VK_KHR_portability_subset
    if(saga_vk_has_device_extension(r->physical,VK_KHR_PORTABILITY_SUBSET_EXTENSION_NAME))dev_exts[dev_ext_count++]=VK_KHR_PORTABILITY_SUBSET_EXTENSION_NAME;
#endif
    VkDeviceCreateInfo dci={0};dci.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;dci.queueCreateInfoCount=1;dci.pQueueCreateInfos=&qci;dci.enabledExtensionCount=dev_ext_count;dci.ppEnabledExtensionNames=dev_exts;
    vr=vkCreateDevice(r->physical,&dci,NULL,&r->device);if(vr!=VK_SUCCESS){saga_vk_set_result("vkCreateDevice",vr);goto fail;}vkGetDeviceQueue(r->device,r->queue_family,0,&r->queue);

    VkSurfaceCapabilitiesKHR caps;vr=vkGetPhysicalDeviceSurfaceCapabilitiesKHR(r->physical,r->surface,&caps);if(vr!=VK_SUCCESS){saga_vk_set_result("vkGetPhysicalDeviceSurfaceCapabilitiesKHR",vr);goto fail;}
    if(!(caps.supportedUsageFlags&VK_IMAGE_USAGE_TRANSFER_DST_BIT)){saga_vk_set_error("swapchain does not support transfer-destination presentation");goto fail;}
    uint32_t fc=0;vr=vkGetPhysicalDeviceSurfaceFormatsKHR(r->physical,r->surface,&fc,NULL);if(vr!=VK_SUCCESS||fc==0){saga_vk_set_result("vkGetPhysicalDeviceSurfaceFormatsKHR",vr);goto fail;}
    VkSurfaceFormatKHR* fs=(VkSurfaceFormatKHR*)calloc(fc,sizeof(VkSurfaceFormatKHR));if(!fs){saga_vk_set_error("out of memory");goto fail;}vkGetPhysicalDeviceSurfaceFormatsKHR(r->physical,r->surface,&fc,fs);
    VkSurfaceFormatKHR chosen=fs[0];
    for(uint32_t i=0;i<fc;i++){if(fs[i].format==VK_FORMAT_R8G8B8A8_UNORM||fs[i].format==VK_FORMAT_R8G8B8A8_SRGB){chosen=fs[i];break;}if(fs[i].format==VK_FORMAT_B8G8R8A8_UNORM||fs[i].format==VK_FORMAT_B8G8R8A8_SRGB)chosen=fs[i];}
    free(fs);r->format=chosen.format;r->bgra=(chosen.format==VK_FORMAT_B8G8R8A8_UNORM||chosen.format==VK_FORMAT_B8G8R8A8_SRGB);
    if(!(r->format==VK_FORMAT_R8G8B8A8_UNORM||r->format==VK_FORMAT_R8G8B8A8_SRGB||r->format==VK_FORMAT_B8G8R8A8_UNORM||r->format==VK_FORMAT_B8G8R8A8_SRGB)){saga_vk_set_error("Vulkan swapchain lacks an RGBA8/BGRA8 format");goto fail;}
    VkExtent2D extent=caps.currentExtent;
    if(extent.width==UINT32_MAX){extent.width=(uint32_t)width;extent.height=(uint32_t)height;if(extent.width<caps.minImageExtent.width)extent.width=caps.minImageExtent.width;if(extent.width>caps.maxImageExtent.width)extent.width=caps.maxImageExtent.width;if(extent.height<caps.minImageExtent.height)extent.height=caps.minImageExtent.height;if(extent.height>caps.maxImageExtent.height)extent.height=caps.maxImageExtent.height;}
    r->extent=extent;
    uint32_t image_count=caps.minImageCount+1;if(caps.maxImageCount&&image_count>caps.maxImageCount)image_count=caps.maxImageCount;
    VkCompositeAlphaFlagBitsKHR alpha=VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
    if(!(caps.supportedCompositeAlpha&alpha)){for(uint32_t bit=1;bit<=VK_COMPOSITE_ALPHA_INHERIT_BIT_KHR;bit<<=1)if(caps.supportedCompositeAlpha&bit){alpha=(VkCompositeAlphaFlagBitsKHR)bit;break;}}
    VkSwapchainCreateInfoKHR sci={0};sci.sType=VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR;sci.surface=r->surface;sci.minImageCount=image_count;sci.imageFormat=chosen.format;sci.imageColorSpace=chosen.colorSpace;sci.imageExtent=extent;sci.imageArrayLayers=1;sci.imageUsage=VK_IMAGE_USAGE_TRANSFER_DST_BIT;sci.imageSharingMode=VK_SHARING_MODE_EXCLUSIVE;sci.preTransform=caps.currentTransform;sci.compositeAlpha=alpha;sci.presentMode=VK_PRESENT_MODE_FIFO_KHR;sci.clipped=VK_TRUE;
    vr=vkCreateSwapchainKHR(r->device,&sci,NULL,&r->swapchain);if(vr!=VK_SUCCESS){saga_vk_set_result("vkCreateSwapchainKHR",vr);goto fail;}
    vr=vkGetSwapchainImagesKHR(r->device,r->swapchain,&r->image_count,NULL);if(vr!=VK_SUCCESS||r->image_count==0){saga_vk_set_result("vkGetSwapchainImagesKHR",vr);goto fail;}r->images=(VkImage*)calloc(r->image_count,sizeof(VkImage));if(!r->images){saga_vk_set_error("out of memory");goto fail;}vr=vkGetSwapchainImagesKHR(r->device,r->swapchain,&r->image_count,r->images);if(vr!=VK_SUCCESS){saga_vk_set_result("vkGetSwapchainImagesKHR",vr);goto fail;}

    r->staging_size=(VkDeviceSize)extent.width*(VkDeviceSize)extent.height*4u;
    VkBufferCreateInfo bci={0};bci.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;bci.size=r->staging_size;bci.usage=VK_BUFFER_USAGE_TRANSFER_SRC_BIT;bci.sharingMode=VK_SHARING_MODE_EXCLUSIVE;vr=vkCreateBuffer(r->device,&bci,NULL,&r->staging);if(vr!=VK_SUCCESS){saga_vk_set_result("vkCreateBuffer",vr);goto fail;}
    VkMemoryRequirements req;vkGetBufferMemoryRequirements(r->device,r->staging,&req);uint32_t mt=saga_vk_choose_memory(r->physical,req.memoryTypeBits,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);if(mt==UINT32_MAX){saga_vk_set_error("no host-visible coherent Vulkan memory for framebuffer staging");goto fail;}
    VkMemoryAllocateInfo mai={0};mai.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;mai.allocationSize=req.size;mai.memoryTypeIndex=mt;vr=vkAllocateMemory(r->device,&mai,NULL,&r->staging_memory);if(vr!=VK_SUCCESS){saga_vk_set_result("vkAllocateMemory",vr);goto fail;}vr=vkBindBufferMemory(r->device,r->staging,r->staging_memory,0);if(vr!=VK_SUCCESS){saga_vk_set_result("vkBindBufferMemory",vr);goto fail;}

    VkCommandPoolCreateInfo cp={0};cp.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;cp.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;cp.queueFamilyIndex=r->queue_family;vr=vkCreateCommandPool(r->device,&cp,NULL,&r->command_pool);if(vr!=VK_SUCCESS){saga_vk_set_result("vkCreateCommandPool",vr);goto fail;}
    VkCommandBufferAllocateInfo cai={0};cai.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;cai.commandPool=r->command_pool;cai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;cai.commandBufferCount=1;vr=vkAllocateCommandBuffers(r->device,&cai,&r->command);if(vr!=VK_SUCCESS){saga_vk_set_result("vkAllocateCommandBuffers",vr);goto fail;}
    VkSemaphoreCreateInfo sem={0};sem.sType=VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO;vr=vkCreateSemaphore(r->device,&sem,NULL,&r->image_available);if(vr==VK_SUCCESS)vr=vkCreateSemaphore(r->device,&sem,NULL,&r->render_finished);if(vr!=VK_SUCCESS){saga_vk_set_result("vkCreateSemaphore",vr);goto fail;}
    VkFenceCreateInfo fi={0};fi.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;fi.flags=VK_FENCE_CREATE_SIGNALED_BIT;vr=vkCreateFence(r->device,&fi,NULL,&r->fence);if(vr!=VK_SUCCESS){saga_vk_set_result("vkCreateFence",vr);goto fail;}

    VkPhysicalDeviceProperties props;vkGetPhysicalDeviceProperties(r->physical,&props);snprintf(r->info,sizeof(r->info),"Vulkan device=%s api=%u.%u.%u swapchain=%ux%u images=%u format=%d",props.deviceName,VK_VERSION_MAJOR(props.apiVersion),VK_VERSION_MINOR(props.apiVersion),VK_VERSION_PATCH(props.apiVersion),extent.width,extent.height,r->image_count,(int)r->format);
    if(out_info&&out_cap){snprintf(out_info,out_cap,"%s",r->info);}if(old_window)SDL_DestroyWindow((SDL_Window*)old_window);if(out_window)*out_window=(uintptr_t)window;return r;
fail:
    saga_vk_renderer_destroy(r);SDL_DestroyWindow(window);return NULL;
}

static int saga_vk_renderer_present(SagaVkRenderer* r,const unsigned char* rgba,int width,int height){
    if(!r||!rgba||width<=0||height<=0){saga_vk_set_error("invalid Vulkan presentation arguments");return 0;}
    if((uint32_t)width!=r->extent.width||(uint32_t)height!=r->extent.height){saga_vk_set_error("Vulkan transfer backend requires framebuffer dimensions equal to current swapchain extent; recreate the renderer after resize");return 0;}
    VkResult vr=vkWaitForFences(r->device,1,&r->fence,VK_TRUE,UINT64_MAX);if(vr!=VK_SUCCESS){saga_vk_set_result("vkWaitForFences",vr);return 0;}vkResetFences(r->device,1,&r->fence);
    uint32_t index=0;vr=vkAcquireNextImageKHR(r->device,r->swapchain,UINT64_MAX,r->image_available,VK_NULL_HANDLE,&index);if(vr==VK_ERROR_OUT_OF_DATE_KHR){saga_vk_set_error("Vulkan swapchain out of date; recreate renderer");return 0;}if(vr!=VK_SUCCESS&&vr!=VK_SUBOPTIMAL_KHR){saga_vk_set_result("vkAcquireNextImageKHR",vr);return 0;}
    void* mapped=NULL;vr=vkMapMemory(r->device,r->staging_memory,0,r->staging_size,0,&mapped);if(vr!=VK_SUCCESS){saga_vk_set_result("vkMapMemory",vr);return 0;}size_t pixels=(size_t)width*(size_t)height;if(!r->bgra){memcpy(mapped,rgba,pixels*4);}else{unsigned char*d=(unsigned char*)mapped;for(size_t i=0;i<pixels;i++){d[4*i]=rgba[4*i+2];d[4*i+1]=rgba[4*i+1];d[4*i+2]=rgba[4*i];d[4*i+3]=rgba[4*i+3];}}vkUnmapMemory(r->device,r->staging_memory);
    vkResetCommandBuffer(r->command,0);VkCommandBufferBeginInfo bi={0};bi.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;vr=vkBeginCommandBuffer(r->command,&bi);if(vr!=VK_SUCCESS){saga_vk_set_result("vkBeginCommandBuffer",vr);return 0;}
    VkImageMemoryBarrier to_copy={0};to_copy.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;to_copy.srcAccessMask=0;to_copy.dstAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;to_copy.oldLayout=VK_IMAGE_LAYOUT_UNDEFINED;to_copy.newLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;to_copy.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;to_copy.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;to_copy.image=r->images[index];to_copy.subresourceRange.aspectMask=VK_IMAGE_ASPECT_COLOR_BIT;to_copy.subresourceRange.levelCount=1;to_copy.subresourceRange.layerCount=1;vkCmdPipelineBarrier(r->command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,NULL,0,NULL,1,&to_copy);
    VkBufferImageCopy copy={0};copy.imageSubresource.aspectMask=VK_IMAGE_ASPECT_COLOR_BIT;copy.imageSubresource.layerCount=1;copy.imageExtent.width=(uint32_t)width;copy.imageExtent.height=(uint32_t)height;copy.imageExtent.depth=1;vkCmdCopyBufferToImage(r->command,r->staging,r->images[index],VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,1,&copy);
    VkImageMemoryBarrier to_present={0};to_present.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;to_present.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;to_present.dstAccessMask=0;to_present.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;to_present.newLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;to_present.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;to_present.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;to_present.image=r->images[index];to_present.subresourceRange.aspectMask=VK_IMAGE_ASPECT_COLOR_BIT;to_present.subresourceRange.levelCount=1;to_present.subresourceRange.layerCount=1;vkCmdPipelineBarrier(r->command,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,0,0,NULL,0,NULL,1,&to_present);
    vr=vkEndCommandBuffer(r->command);if(vr!=VK_SUCCESS){saga_vk_set_result("vkEndCommandBuffer",vr);return 0;}
    VkPipelineStageFlags wait_stage=VK_PIPELINE_STAGE_TRANSFER_BIT;VkSubmitInfo submit={0};submit.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO;submit.waitSemaphoreCount=1;submit.pWaitSemaphores=&r->image_available;submit.pWaitDstStageMask=&wait_stage;submit.commandBufferCount=1;submit.pCommandBuffers=&r->command;submit.signalSemaphoreCount=1;submit.pSignalSemaphores=&r->render_finished;vr=vkQueueSubmit(r->queue,1,&submit,r->fence);if(vr!=VK_SUCCESS){saga_vk_set_result("vkQueueSubmit",vr);return 0;}
    VkPresentInfoKHR present={0};present.sType=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR;present.waitSemaphoreCount=1;present.pWaitSemaphores=&r->render_finished;present.swapchainCount=1;present.pSwapchains=&r->swapchain;present.pImageIndices=&index;vr=vkQueuePresentKHR(r->queue,&present);if(vr==VK_ERROR_OUT_OF_DATE_KHR){saga_vk_set_error("Vulkan swapchain out of date; recreate renderer");return 0;}if(vr!=VK_SUCCESS&&vr!=VK_SUBOPTIMAL_KHR){saga_vk_set_result("vkQueuePresentKHR",vr);return 0;}return 1;
}
*/
import "C"

import (
	"fmt"
	"unsafe"
)

func desktopVulkanRendererCompiled() bool { return true }

func desktopVulkanRendererCreate(oldWindow uintptr, title string, width, height int) (renderer uintptr, newWindow uintptr, info string, err error) {
	if oldWindow == 0 {
		return 0, 0, "", fmt.Errorf("window closed")
	}
	desktopOnThread(func() {
		ct := C.CString(title)
		defer C.free(unsafe.Pointer(ct))
		var nw C.uintptr_t
		buf := make([]byte, 1024)
		r := C.saga_vk_renderer_create(C.uintptr_t(oldWindow), ct, C.int(width), C.int(height), &nw, (*C.char)(unsafe.Pointer(&buf[0])), C.size_t(len(buf)))
		if r == nil {
			err = fmt.Errorf("%s", C.GoString(C.saga_vk_last_error()))
			return
		}
		renderer = uintptr(unsafe.Pointer(r))
		newWindow = uintptr(nw)
		info = C.GoString((*C.char)(unsafe.Pointer(&buf[0])))
	})
	return
}
func desktopVulkanRendererDestroy(handle uintptr) {
	if handle != 0 {
		desktopOnThread(func() { C.saga_vk_renderer_destroy((*C.SagaVkRenderer)(unsafe.Pointer(handle))) })
	}
}
func desktopVulkanRendererPresent(handle uintptr, rgba []byte, width, height int) (err error) {
	if handle == 0 || len(rgba) != width*height*4 {
		return fmt.Errorf("invalid Vulkan renderer/framebuffer")
	}
	desktopOnThread(func() {
		if C.saga_vk_renderer_present((*C.SagaVkRenderer)(unsafe.Pointer(handle)), (*C.uchar)(unsafe.Pointer(&rgba[0])), C.int(width), C.int(height)) == 0 {
			err = fmt.Errorf("%s", C.GoString(C.saga_vk_last_error()))
		}
	})
	return
}
