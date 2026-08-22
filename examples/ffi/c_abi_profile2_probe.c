#include <stdint.h>
#include <stdlib.h>
typedef struct { int32_t x; double y; } Pair;
Pair pair_twice(Pair a) { Pair r = { a.x * 2, a.y * 2.0 }; return r; }
int64_t apply_cb(int64_t (*cb)(int64_t)) { return cb(32) + 1; }
void *make_owned8(void) { return malloc(8); }
