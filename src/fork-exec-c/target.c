/*
 * Copyright(c) The Maintainers of Nanvix.
 * Licensed under the MIT License.
 */

/*
 * execv() target for the fork+exec vfsd-I/O reproducer.
 *
 * This program is loaded into the guest ramfs at "/target" and is execv()'d by
 * the caller (fork-exec-c.elf). After exec, it does two things:
 *
 *   1. Writes a marker to stdout (kernel IKC path -- no vfsd involvement). This
 *      proves the exec'd image is actually running.
 *   2. Performs a filesystem read via vfsd: it opens and reads its own ELF file
 *      at "/target" (guaranteed present in the ramfs). This is the operation
 *      that hangs when the process was reached via fork()+execv().
 *
 * On a correct system it prints both markers and exits 0. On the buggy system
 * it prints only the first marker and then hangs forever inside the vfsd read.
 */

#include <fcntl.h>
#include <unistd.h>

#define SELF_PATH "/target"

static void emit(const char *s)
{
    /* Write directly to stdout (fd 1). On Nanvix this is routed to the kernel
       via IKC and does NOT go through vfsd, so it works in an exec'd image. */
    const char *p = s;
    while (*p) {
        p++;
    }
    (void)write(STDOUT_FILENO, s, (size_t)(p - s));
}

int main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;

    emit("TARGET-STARTED\n");

    /* The vfsd filesystem read that hangs after fork()+execv(). */
    int fd = open(SELF_PATH, O_RDONLY);
    if (fd < 0) {
        emit("TARGET-OPEN-FAILED\n");
        return (1);
    }

    char buf[4];
    ssize_t n = read(fd, buf, sizeof(buf));
    (void)close(fd);

    if (n != (ssize_t)sizeof(buf) || buf[0] != 0x7f || buf[1] != 'E' ||
        buf[2] != 'L' || buf[3] != 'F') {
        emit("TARGET-READ-FAILED\n");
        return (1);
    }

    /* Only reached if the vfsd read returned. */
    emit("TARGET-READ-OK\n");
    emit("ok\n");
    return (0);
}
