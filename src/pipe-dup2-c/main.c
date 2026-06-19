/*
 * Copyright(c) The Maintainers of Nanvix.
 * Licensed under the MIT License.
 */

/*
 * Reproducer: dup2() of a pipe onto a standard stream (stdin/stdout/stderr)
 * does not redirect that stream.
 *
 * Background
 * ----------
 * On Nanvix the file-descriptor space is range-partitioned by subsystem
 * rather than backed by a single unified descriptor table:
 *
 *   - 0,1,2          : the standard streams, routed to the kernel via IKC.
 *   - 1024 and above : VFS / pipe descriptors (served by vfsd).
 *   - 2048 and above : socket descriptors (served by networkd).
 *
 * Because these ranges are owned by different subsystems, dup2(oldfd, newfd)
 * cannot move a descriptor from one range onto a number owned by another. In
 * particular, dup2(pipe_fd, STDOUT_FILENO) cannot make fd 1 refer to the pipe:
 * fd 1 stays wired to the kernel console. This breaks the classic
 * "pipe + dup2 onto 0/1/2 + exec" pattern that shells and subprocess libraries
 * use to redirect a child's standard streams.
 *
 * What this program demonstrates (run in standalone mode)
 * -------------------------------------------------------
 *   DUP2-START       - the test starts.
 *   PIPE-OK          - a plain pipe() round-trips data (pipes themselves work).
 *   DUP2-RET-OK      - dup2(pipe_write_end, STDOUT_FILENO) returned without
 *                      error.
 *   DUP2-REDIRECT-OK - data written to STDOUT_FILENO afterwards was actually
 *                      readable from the pipe.
 *   ok               - the whole sequence succeeded.
 *
 * Correct behavior : all markers print and the process exits 0.
 * Buggy behavior   : the redirect does not happen, and the process exits
 *                    non-zero. Two failure shapes are possible and both are
 *                    detected here:
 *                      - dup2() itself returns an error  -> DUP2-RET-FAILED
 *                        (this is what stock Nanvix does: fd 1 is a kernel-IKC
 *                         descriptor in a different range than the pipe, so the
 *                         duplication is refused);
 *                      - dup2() "succeeds" but the write still goes to the
 *                        console -> DUP2-REDIRECT-FAILED.
 *
 * The test never blocks: the read end is set non-blocking before the final
 * read, so a missing redirect returns immediately instead of hanging.
 *
 * All diagnostic markers are written to stderr (fd 2), NOT stdout, because the
 * test deliberately attempts to rewire stdout; routing markers through stderr
 * keeps them out of the pipe under test regardless of whether dup2 took effect.
 */

#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>

#define MARKER "REDIRECTED-VIA-PIPE"

static void emit(const char *s)
{
    const char *p = s;
    while (*p) {
        p++;
    }
    /* Write to stderr so these markers never land in the pipe under test. */
    (void)write(STDERR_FILENO, s, (size_t)(p - s));
}

int main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;

    emit("DUP2-START\n");

    int p[2];
    if (pipe(p) != 0) {
        emit("PIPE-FAILED\n");
        return (1);
    }

    /* Sanity: a plain pipe round-trips data on Nanvix. */
    const char probe[] = "AB";
    if (write(p[1], probe, sizeof(probe) - 1) != (ssize_t)(sizeof(probe) - 1)) {
        emit("PIPE-WRITE-FAILED\n");
        return (1);
    }
    char pbuf[2] = {0, 0};
    if (read(p[0], pbuf, sizeof(pbuf)) != (ssize_t)sizeof(pbuf) ||
        pbuf[0] != 'A' || pbuf[1] != 'B') {
        emit("PIPE-READ-FAILED\n");
        return (1);
    }
    emit("PIPE-OK\n");

    /* Attempt to redirect stdout onto the pipe's write end. */
    if (dup2(p[1], STDOUT_FILENO) < 0) {
        emit("DUP2-RET-FAILED\n");
        return (1);
    }
    emit("DUP2-RET-OK\n");

    /* If the redirect took effect, this write lands in the pipe; otherwise it
       goes to the kernel console. */
    if (write(STDOUT_FILENO, MARKER, strlen(MARKER)) < 0) {
        emit("STDOUT-WRITE-FAILED\n");
        return (1);
    }

    /* Make the read end non-blocking so a failed redirect does not hang. */
    int flags = fcntl(p[0], F_GETFL, 0);
    if (flags < 0 || fcntl(p[0], F_SETFL, flags | O_NONBLOCK) < 0) {
        emit("FCNTL-FAILED\n");
        return (1);
    }

    char buf[64];
    ssize_t n = read(p[0], buf, sizeof(buf));
    if (n != (ssize_t)strlen(MARKER) || memcmp(buf, MARKER, (size_t)n) != 0) {
        /* The bytes written to STDOUT_FILENO did not reach the pipe: dup2 did
           not redirect the standard stream. */
        emit("DUP2-REDIRECT-FAILED\n");
        return (1);
    }
    emit("DUP2-REDIRECT-OK\n");

    emit("ok\n");
    return (0);
}
