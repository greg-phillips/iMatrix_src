/*
 * Standalone test program to demonstrate TTY diagnostics
 * Compile with: gcc -o test_tty test_tty_diagnostic.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <termios.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/select.h>

#define TTY_DEBUG(fmt, ...) printf("[TTY DEBUG] " fmt "\n", ##__VA_ARGS__)

static struct termios orig_termios;
static int tty_initialized = 0;

int init_tty(void) {
    TTY_DEBUG("Initializing TTY interface");
    
    // Check if stdin is a terminal
    if (!isatty(STDIN_FILENO)) {
        TTY_DEBUG("stdin is not a terminal - errno=%d (%s)", errno, strerror(errno));
        return -1;
    }
    
    TTY_DEBUG("stdin is a terminal, device: %s", ttyname(STDIN_FILENO));
    
    // Get current terminal settings
    if (tcgetattr(STDIN_FILENO, &orig_termios) < 0) {
        TTY_DEBUG("tcgetattr failed: errno=%d (%s)", errno, strerror(errno));
        return -1;
    }
    
    TTY_DEBUG("Got terminal attributes successfully");
    
    // Set non-blocking mode
    int flags = fcntl(STDIN_FILENO, F_GETFL, 0);
    if (flags < 0) {
        TTY_DEBUG("fcntl(F_GETFL) failed: errno=%d (%s)", errno, strerror(errno));
        return -1;
    }
    
    if (fcntl(STDIN_FILENO, F_SETFL, flags | O_NONBLOCK) < 0) {
        TTY_DEBUG("fcntl(F_SETFL) failed: errno=%d (%s)", errno, strerror(errno));
        return -1;
    }
    
    TTY_DEBUG("Set non-blocking mode successfully");
    
    // Configure raw mode
    struct termios raw = orig_termios;
    raw.c_iflag &= ~(BRKINT | ICRNL | INPCK | ISTRIP | IXON);
    raw.c_oflag &= ~(OPOST);
    raw.c_cflag |= (CS8);
    raw.c_lflag &= ~(ECHO | ICANON | IEXTEN | ISIG);
    raw.c_cc[VMIN] = 0;
    raw.c_cc[VTIME] = 0;
    
    if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw) < 0) {
        TTY_DEBUG("tcsetattr failed: errno=%d (%s)", errno, strerror(errno));
        return -1;
    }
    
    TTY_DEBUG("TTY initialization complete - raw mode enabled");
    tty_initialized = 1;
    return 0;
}

void restore_tty(void) {
    if (tty_initialized) {
        tcsetattr(STDIN_FILENO, TCSAFLUSH, &orig_termios);
        TTY_DEBUG("Restored original terminal settings");
    }
}

int has_input(void) {
    fd_set readfds;
    struct timeval tv;
    int retval;
    
    FD_ZERO(&readfds);
    FD_SET(STDIN_FILENO, &readfds);
    
    tv.tv_sec = 0;
    tv.tv_usec = 0;
    
    retval = select(STDIN_FILENO + 1, &readfds, NULL, NULL, &tv);
    
    if (retval < 0) {
        TTY_DEBUG("select error: errno=%d (%s)", errno, strerror(errno));
        return 0;
    }
    
    if (retval > 0 && FD_ISSET(STDIN_FILENO, &readfds)) {
        TTY_DEBUG("Input available from select()");
        return 1;
    }
    
    return 0;
}

int main(void) {
    printf("=== TTY Diagnostic Test ===\n");
    printf("This test will show detailed TTY debugging information\n");
    printf("Press 'q' to quit\n\n");
    
    if (init_tty() != 0) {
        printf("Failed to initialize TTY!\n");
        printf("Are you running this from a terminal?\n");
        return 1;
    }
    
    printf("\nWaiting for input (TTY debug messages will appear)...\n\n");
    
    while (1) {
        if (has_input()) {
            unsigned char ch;
            int n = read(STDIN_FILENO, &ch, 1);
            
            if (n == 1) {
                if (ch >= 32 && ch < 127) {
                    TTY_DEBUG("Read character '%c' (0x%02X)", ch, ch);
                    printf("You pressed: '%c'\n", ch);
                } else {
                    TTY_DEBUG("Read non-printable character (0x%02X)", ch);
                    printf("You pressed: [0x%02X]\n", ch);
                }
                
                if (ch == 'q' || ch == 'Q') {
                    printf("Exiting...\n");
                    break;
                }
            } else if (n < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
                TTY_DEBUG("read error: errno=%d (%s)", errno, strerror(errno));
            }
        }
        
        usleep(10000); // 10ms delay
    }
    
    restore_tty();
    return 0;
}