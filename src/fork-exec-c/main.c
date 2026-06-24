/*
 * Copyright(c) The Maintainers of Nanvix.
 * Licensed under the MIT License.
 */

/*
 * Reproducer: a fork()+execv()'d process hangs on its first vfsd filesystem
 * I/O operation.
 *
 * Background
 * ----------
 * On Nanvix, execv() replaces the calling process's image and gives it a NEW
 * main-thread identifier (the old thread is retired). Filesystem reads/writes
 * are served by the vfsd daemon through a kernel push/pull rendezvous that is
 * keyed by the client's (pid, tid). After fork()+execv(), the exec'd image's
 * first vfsd request never completes -- the client blocks forever -- which
 * makes any "fork then exec a program that touches the filesystem" workload
 * (e.g. a Python subprocess, or `python script.py` spawned from a server) hang.
 *
 * What this program demonstrates (run in standalone mode)
 * -------------------------------------------------------
 *   CALLER-START      - the init/caller process starts.
 *   PARENT-READ-OK    - the caller reads /target via vfsd successfully. This is
 *                       the SAME vfsd read the target performs, proving vfsd I/O
 *                       works from an ordinary (non-fork+exec) process.
 *   TARGET-STARTED    - the child's execv("/target") succeeded and the new image
 *                       is running (so fork() and execv() themselves work).
 *   TARGET-READ-OK    - the exec'd image completed its vfsd read.  <-- expected
 *                       on a correct system; NEVER printed on the buggy system.
 *   ok                - the whole sequence succeeded.
 *
 * Correct behavior : all markers print and the process exits 0.
 * Buggy behavior   : prints up to TARGET-STARTED, then hangs forever in the
 *                    target's vfsd read (the run times out).
 *
 * The target program is bundled into the ramfs at "/target" by the test
 * harness (see .nanvix/z.py SUITE_RAMFS_LIBS).
 */

#include <fcntl.h>
#include <sys/wait.h>
#include <unistd.h>

#define TARGET_PATH "/target"

static void emit(const char *s)
{
    const char *p = s;
    while (*p) {
        p++;
    }
    (void)write(STDOUT_FILENO, s, (size_t)(p - s));
}

/* Reads the first 4 bytes of /target via vfsd and checks the ELF magic.
   Returns 0 on success, -1 on failure. */
static int read_target_magic(void)
{
    int fd = open(TARGET_PATH, O_RDONLY);
    if (fd < 0) {
        return (-1);
    }
    char buf[4];
    ssize_t n = read(fd, buf, sizeof(buf));
    (void)close(fd);
    if (n != (ssize_t)sizeof(buf) || buf[0] != 0x7f || buf[1] != 'E' ||
        buf[2] != 'L' || buf[3] != 'F') {
        return (-1);
    }
    return (0);
}

int main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;

    emit("CALLER-START\n");

    /* Control: the same vfsd read, but from this ordinary process. This works,
       establishing that vfsd I/O is fine outside the fork+exec path. */
    if (read_target_magic() != 0) {
        emit("PARENT-READ-FAILED\n");
        return (1);
    }
    emit("PARENT-READ-OK\n");

    /* Now the failing case: fork, then exec a program that does the same read. */
    emit("CALLER-FORKING\n");
    pid_t pid = fork();
    if (pid < 0) {
        emit("FORK-FAILED\n");
        return (1);
    }

    if (pid == 0) {
        /* Child: replace image with the target. On success this never returns. */
        char *const child_argv[] = {(char *)"target", (char *)0};
        execv(TARGET_PATH, child_argv);
        /* Only reached if execv() failed. */
        emit("EXECV-FAILED\n");
        _exit(127);
    }

    /* Parent: wait for the exec'd child. On the buggy system this blocks
       forever because the child is stuck in its vfsd read. */
    int status = 0;
    pid_t w = waitpid(pid, &status, 0);
    if (w != pid) {
        emit("WAITPID-FAILED\n");
        return (1);
    }
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        emit("CHILD-NONZERO-EXIT\n");
        return (1);
    }

    emit("ok\n");
    return (0);
}
