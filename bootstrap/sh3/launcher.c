/* Saga SH-3 launcher. Language-neutral: locates sibling SH3 VM and canonical
 * Saga-generated kernel bytecode, then transfers control with the user's argv.
 * No Saga syntax or language semantics are implemented here. */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static char *join_sibling(const char *argv0, const char *name) {
    const char *slash = strrchr(argv0, '/');
    size_t d = slash ? (size_t)(slash - argv0 + 1) : 0;
    char *p = malloc(d + strlen(name) + 1);
    if (!p) { fputs("saga-sh3: out of memory\n", stderr); exit(70); }
    if (d) memcpy(p, argv0, d);
    strcpy(p + d, name);
    return p;
}

int main(int argc, char **argv) {
    char *vm = join_sibling(argv[0], "sh3vm");
    const char *base = strrchr(argv[0], '/');
    base = base ? base + 1 : argv[0];
    const char *image_name = !strcmp(base, "sagac") ? "sagac.sbc" : "kernel.sbc";
    char *kernel = join_sibling(argv[0], image_name);
    char **av = calloc((size_t)argc + 2u, sizeof(char *));
    if (!av) { fputs("saga-sh3: out of memory\n", stderr); return 70; }
    av[0] = vm;
    av[1] = kernel;
    for (int i = 1; i < argc; ++i) av[i + 1] = argv[i];
    av[argc + 1] = NULL;
    execv(vm, av);
    fprintf(stderr, "saga-sh3: cannot execute %s: %s\n", vm, strerror(errno));
    return 69;
}
