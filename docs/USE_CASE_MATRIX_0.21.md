# Saga 0.21.0 use-case matrix

| Use case | 0.20 | 0.21 | Evidence / boundary |
|---|---|---|---|
| CLI / algorithms | strong | strong | retained Standard Core + SH-3 |
| Web frontend | weak | **usable baseline** | SH-3 browser bundle, DOM/value/storage/click host API |
| Mobile app | weak | **PWA baseline** | installable/offline PWA; not native App Store SDK |
| HTTP backend | basic | **stronger** | real listen/accept/respond server, close-race handling |
| Persistent app data | basic | **stronger** | optimistic transaction/rollback/conflict detection |
| 2D game | good | good | retained 101-function game surface including 2D |
| 3D graphics | weak | **usable baseline** | CPU perspective/depth renderer + OBJ loading |
| GPU compute/shaders | baseline | baseline | retained SIR1 fragment/compute |
| Systems introspection | limited | **stronger** | platform/arch/cpu_count/page_size |
| Bare metal | baseline | baseline | retained Cortex-M0/STM32 profile |
| Native Android/iOS | weak | still limited | PWA helps deployment but is not native mobile runtime validation |
| AAA 3D engine | insufficient | still insufficient | CPU 3D foundation only; no PBR/animation/scene/GPU mesh stack |
| OS/kernel | early | early | bare-metal/MMIO exists; no full kernel/runtime ecosystem |

The purpose of 0.21 is to turn the largest practical gaps into usable baselines while preserving the small beginner-facing language surface and SH-3 self-hosting qualification.
