//go:build sagaobject && cgo

package main

/*
#include <stddef.h>
typedef struct {
    const char* id;
    const unsigned char* source;
    size_t source_len;
    const unsigned char* edges_json;
    size_t edges_len;
} SagaObjectModule;
*/
import "C"

import (
	"encoding/json"
	"fmt"
	"unsafe"
)

//export SagaRunObjectGraph
func SagaRunObjectGraph(entry *C.char, modules *C.SagaObjectModule, count C.size_t) C.int {
	if entry == nil {
		fmt.Println("SAGA-I001: native object entry is missing")
		return 65
	}
	sources := map[string]string{}
	edges := map[string]string{}
	items := unsafe.Slice(modules, int(count))
	for _, item := range items {
		if item.id == nil || item.source == nil {
			fmt.Println("SAGA-I001: malformed native object descriptor")
			return 65
		}
		id := C.GoString(item.id)
		source := C.GoBytes(unsafe.Pointer(item.source), C.int(item.source_len))
		sources[id] = string(source)
		if item.edges_json != nil && item.edges_len > 0 {
			raw := C.GoBytes(unsafe.Pointer(item.edges_json), C.int(item.edges_len))
			var local map[string]string
			if err := json.Unmarshal(raw, &local); err != nil {
				fmt.Println("SAGA-I001: invalid native object edge metadata:", err)
				return 65
			}
			for spec, target := range local {
				edges[id+"\x00"+spec] = target
			}
		}
	}
	if err := executeObjectGraph(C.GoString(entry), sources, edges); err != nil {
		return C.int(printDiagnostic(err))
	}
	return 0
}
