/*
 * Copyright(c) The Maintainers of Nanvix.
 * Licensed under the MIT License.
 */

/*
 * Reproducer: a socket is SHARED (not reference-counted) across fork(), so a
 * child that close()s an inherited socket destroys the PARENT's socket too.
 *
 * Background
 * ----------
 * On Nanvix, filesystem descriptors and socket descriptors are owned by
 * different subsystems. The vfsd daemon duplicates a process's open files on
 * fork() (it implements a ForkClone handler), so files behave per POSIX: each
 * process holds an independent reference and closing one does not affect the
 * other. networkd, which backs AF_INET sockets, does NOT do this -- it maps a
 * guest socket descriptor to a host socket by a fixed arithmetic offset and
 * keeps no per-process reference count. After fork(), parent and child name
 * the very same underlying host socket, and the first close() in EITHER process
 * tears it down for BOTH.
 *
 * POSIX requires the opposite: fork() duplicates the parent's open socket
 * descriptors, each holding an independent reference to the same open socket
 * description; the socket is only released once the LAST descriptor referring
 * to it is closed. A child closing its copy must leave the parent's socket
 * fully usable. This is what every mainstream OS (Linux, the BSDs, etc.) does,
 * and it is what server code relies on when it forks per-connection workers.
 *
 * What this program demonstrates (run in standalone mode with host networking)
 * ---------------------------------------------------------------------------
 *   SOCKFORK-START   - the test starts.
 *   SOCKET-OK        - the parent created and bound an AF_INET socket and
 *                      getsockname() on it succeeds (the socket is alive).
 *   CHILD-CLOSED     - the child closed its inherited copy of the socket and
 *                      exited.
 *   SOCKET-SURVIVED  - getsockname() on the PARENT's socket still succeeds
 *                      after the child closed its copy.  <-- on a correct
 *                      system; on Nanvix the parent's socket has been torn
 *                      down, so this FAILS.
 *   ok               - the whole sequence succeeded.
 *
 * Correct behavior : all markers print and the process exits 0.
 * Buggy behavior   : prints SOCKET-KILLED-BY-CHILD-CLOSE and exits non-zero
 *                    (the child's close() destroyed the parent's socket).
 *
 * Requires nanvixd to be started with -allow-host-networking (the harness adds
 * this automatically for suites in SUITES_REQUIRING_NETWORKING).
 */

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>

static void emit(const char *s)
{
    const char *p = s;
    while (*p) {
        p++;
    }
    (void)write(STDOUT_FILENO, s, (size_t)(p - s));
}

/* Probe whether a socket descriptor is still alive via getsockname().
   Returns 0 if the descriptor names a live socket, -1 otherwise. */
static int socket_alive(int fd)
{
    struct sockaddr addrbuf;
    socklen_t addrlen = sizeof(addrbuf);
    return (getsockname(fd, &addrbuf, &addrlen) == 0) ? 0 : -1;
}

int main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;

    emit("SOCKFORK-START\n");

    /* Create and bind an AF_INET socket in the parent. */
    int s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (s < 0) {
        emit("SOCKET-CREATE-FAILED\n");
        return (1);
    }

    struct sockaddr_in sa = {
        .sin_len = sizeof(sa),
        .sin_family = AF_INET,
        .sin_port = htons(2609),
        .sin_addr = {.s_addr = htonl(0x7f000001)}, /* 127.0.0.1 */
    };
    if (bind(s, (const struct sockaddr *)&sa, sizeof(sa)) != 0) {
        emit("SOCKET-BIND-FAILED\n");
        return (1);
    }

    /* The socket is alive before fork(). */
    if (socket_alive(s) != 0) {
        emit("SOCKET-PREFORK-DEAD\n");
        return (1);
    }
    emit("SOCKET-OK\n");

    pid_t pid = fork();
    if (pid < 0) {
        emit("FORK-FAILED\n");
        return (1);
    }

    if (pid == 0) {
        /* Child: close its inherited copy of the socket and exit. Under POSIX
           this only drops the child's reference; the parent's stays open. */
        int r = close(s);
        _exit(r == 0 ? 0 : 1);
    }

    /* Parent: wait for the child to finish closing its copy. */
    int status = 0;
    if (waitpid(pid, &status, 0) != pid) {
        emit("WAITPID-FAILED\n");
        return (1);
    }
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        emit("CHILD-CLOSE-FAILED\n");
        return (1);
    }
    emit("CHILD-CLOSED\n");

    /* The parent's socket must still be alive. If the socket was shared rather
       than reference-counted across fork(), the child's close() has destroyed
       it and this probe fails. */
    if (socket_alive(s) != 0) {
        emit("SOCKET-KILLED-BY-CHILD-CLOSE\n");
        (void)close(s);
        return (1);
    }
    emit("SOCKET-SURVIVED\n");

    (void)close(s);
    emit("ok\n");
    return (0);
}
